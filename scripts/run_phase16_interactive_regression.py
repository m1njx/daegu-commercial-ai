# -*- coding: utf-8 -*-
"""Phase 16 regressions for browser-discovered demo, widget and wording defects."""

from __future__ import annotations

import ast
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.recommendation.explain import generate_explanation
from src.recommendation.feature_builder import build_dong_industry_features
from src.recommendation.improved import generate_improved_explanation
from src.recommendation.personalization import BASELINE_WEIGHTS, WEIGHT_PRESETS
from src.recommendation.ranking import rank_locations
from src.recommendation.scoring import calculate_component_scores, compute_total_score
from src.recommendation.transit_enhanced import calculate_enhanced_scores, generate_enhanced_explanation

DEMO_EXPECTED = [
    ("카페", "2030", "기본 균형형", "신암4동", 77.75),
    ("한식", "전체", "배후 수요 집중형 (대형 매장/안정형)", "상인1동", 77.47),
    ("미용실", "2030", "기본 균형형", "칠성동", 75.45),
    ("학원", "10대", "타깃 고객 집중형 (트렌디/특화 소비)", "범어1동", 84.40),
    ("종합소매", "전체", "기본 균형형", "상인1동", 72.25),
    ("숙박", "2030", "기본 균형형", "칠성동", 75.90),
]
BAD_PARTICLES = ("비중가", "인원가", "여건가", "미크로")


def load_inputs():
    dong = pd.read_parquet(ROOT / "data/processed/feature_mart/commercial_feature_mart_dong.parquet")
    store = pd.read_parquet(ROOT / "data/processed/feature_mart/store_spatial_features.parquet")
    bus = pd.read_parquet(ROOT / "data/processed/transit/bus/daegu_bus_dong_features.parquet")
    bus_cols = [
        "dong_bus_stop_count", "dong_daily_bus_boarding", "dong_daily_bus_alighting",
        "dong_daily_bus_total", "dong_bus_stop_density", "dong_bus_ridership_per_stop",
        "avg_dist_to_bus_m", "ratio_stores_in_bus_300m",
    ]
    for col in bus_cols:
        dong[col] = bus[col].values
    return dong, store


def integrated(industry, target, weights, dong, store):
    feat, meta = build_dong_industry_features(industry, target, dong, store)
    for col in (
        "dong_bus_stop_count", "dong_daily_bus_boarding", "dong_daily_bus_alighting",
        "dong_daily_bus_total", "dong_bus_stop_density", "dong_bus_ridership_per_stop",
        "avg_dist_to_bus_m", "ratio_stores_in_bus_300m",
    ):
        feat[col] = dong[col].values
    out = rank_locations(calculate_enhanced_scores(
        feat, weights=weights, candidate="candidate_b", is_improved=True,
        min_stores=1, discount_factor=0.50,
    ))
    return out, meta


def extract_demo_presets():
    tree = ast.parse((ROOT / "app/app.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "DEMO_SCENARIOS" for t in node.targets):
            presets = []
            for _, value in zip(node.value.keys, node.value.values):
                if isinstance(value, ast.Dict):
                    values = {ast.literal_eval(k): ast.literal_eval(v) for k, v in zip(value.keys, value.values)
                              if isinstance(v, ast.Constant)}
                    presets.append(values["preset"])
            return presets
    raise AssertionError("DEMO_SCENARIOS not found")


def run():
    passed = 0
    app_text = (ROOT / "app/app.py").read_text(encoding="utf-8")

    # 1. Every demo preset resolves through the production dictionary.
    demo_presets = extract_demo_presets()
    assert len(demo_presets) == 6 and all(p in WEIGHT_PRESETS for p in demo_presets)
    passed += 1

    # 2. Preset vectors retain six non-negative components summing to one.
    assert WEIGHT_PRESETS["기본 균형형"] == BASELINE_WEIGHTS
    for weights in WEIGHT_PRESETS.values():
        assert set(weights) == set(BASELINE_WEIGHTS)
        assert all(v >= 0 for v in weights.values()) and math.isclose(sum(weights.values()), 1.0)
    passed += 1

    dong, store = load_inputs()

    # 3-8. All six real demo configurations resolve, score and preserve their outputs.
    for industry, target, preset, expected_dong, expected_score in DEMO_EXPECTED:
        out, _ = integrated(industry, target, WEIGHT_PRESETS[preset], dong, store)
        assert out.iloc[0]["adm_nm"].endswith(expected_dong)
        assert math.isclose(float(out.iloc[0]["total_score"]), expected_score, abs_tol=0.06)
        assert len(out) == 150 and np.isfinite(out["total_score"]).all()
        passed += 1

    # 9. AppTest executes all demo callbacks without exception or user-visible widget warning.
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(ROOT / "app/app.py"), default_timeout=45).run(timeout=45)
    assert len(at.exception) == 0
    demo_widget = next(widget for widget in at.selectbox if widget.label == "🎬 심사위원 데모 시나리오")
    demo_options = list(demo_widget.options)
    assert len(demo_options) == 7
    for option in demo_options[1:]:
        demo_widget.set_value(option)
        at.run(timeout=45)
        assert len(at.exception) == 0, (option, at.exception)
        warning_text = " ".join(str(w.value) for w in at.warning)
        assert "Session State API" not in warning_text
        assert "created with a default value" not in warning_text
    passed += 1

    # 10. User-facing preset and explanation terminology is exact.
    user_text = app_text + "\n" + (ROOT / "src/recommendation/personalization.py").read_text(encoding="utf-8")
    assert "교통/유동인구 우선형" not in user_text
    assert "대중교통 접근성 우선형 (도보 테이크아웃)" in user_text
    assert all(term not in user_text for term in BAD_PARTICLES)
    passed += 1

    # 11. 3 models x 6 scenarios x Top5: particle/typo and grounding regression.
    generators = [generate_explanation, generate_improved_explanation, generate_enhanced_explanation]
    explanation_count = 0
    for industry, target, preset, _, _ in DEMO_EXPECTED:
        feat, meta = build_dong_industry_features(industry, target, dong, store)
        for col in (
            "dong_bus_stop_count", "dong_daily_bus_boarding", "dong_daily_bus_alighting",
            "dong_daily_bus_total", "dong_bus_stop_density", "dong_bus_ridership_per_stop",
            "avg_dist_to_bus_m", "ratio_stores_in_bus_300m",
        ):
            feat[col] = dong[col].values
        weights = WEIGHT_PRESETS[preset]
        frames = [
            rank_locations(compute_total_score(calculate_component_scores(feat.copy()), weights)),
            rank_locations(calculate_enhanced_scores(feat.copy(), weights=weights, candidate="baseline", is_improved=True)),
            rank_locations(calculate_enhanced_scores(feat.copy(), weights=weights, candidate="candidate_b", is_improved=True)),
        ]
        for frame, generator in zip(frames, generators):
            for _, row in frame.head(5).iterrows():
                exp = generator(row, meta)
                text = " ".join([exp["summary_sentence"], *exp["strengths"], *exp["cautions"]])
                assert all(term not in text for term in BAD_PARTICLES)
                assert "유동인구" not in text
                assert exp["rank"] == int(row["rank"])
                assert math.isclose(exp["total_score"], float(row["total_score"]), abs_tol=1e-9)
                explanation_count += 1
    assert explanation_count == 90
    passed += 1

    # 12. UI templates themselves do not reconstruct the broken particles.
    assert "{desc_html}가" not in app_text
    assert "집적도와 비중이" in app_text
    assert "일평균 승하차 규모가" in app_text
    assert "부설주차면 공급 여건이" in app_text
    passed += 1

    assert passed == 12
    print("PHASE 16: 12/12 PASS")
    print("Demo runtime: 6/6; explanation particles: 90/90")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if run() else 1)
