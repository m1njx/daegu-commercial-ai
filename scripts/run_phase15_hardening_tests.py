# -*- coding: utf-8 -*-
"""Phase 15 final-submission runtime, schema, claim and UI regression suite."""

from __future__ import annotations

import codecs
import io
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
from src.recommendation.personalization import BASELINE_WEIGHTS, WEIGHT_PRESETS, validate_and_normalize_weights
from src.recommendation.ranking import rank_locations
from src.recommendation.scoring import calculate_component_scores, compute_total_score
from src.recommendation.transit_enhanced import calculate_enhanced_scores, generate_enhanced_explanation

BUS_COLS = [
    "dong_bus_stop_count", "dong_daily_bus_boarding", "dong_daily_bus_alighting",
    "dong_daily_bus_total", "dong_bus_stop_density", "dong_bus_ridership_per_stop",
    "avg_dist_to_bus_m", "ratio_stores_in_bus_300m",
]
REQUIRED = {
    "rank", "adm_cd2", "adm_nm", "total_score", "demand_score", "target_fit_score",
    "competition_score", "accessibility_score", "parking_score", "industry_fit_score",
    "cat_store_count", "is_unentered", "market_status",
}
SCENARIOS = [
    ("카페", "2030"), ("한식", "전체"), ("미용실", "2030"),
    ("학원", "10대"), ("종합소매", "전체"), ("숙박", "2030"),
]


def load_inputs():
    dong = pd.read_parquet(ROOT / "data/processed/feature_mart/commercial_feature_mart_dong.parquet")
    store = pd.read_parquet(ROOT / "data/processed/feature_mart/store_spatial_features.parquet")
    bus = pd.read_parquet(ROOT / "data/processed/transit/bus/daegu_bus_dong_features.parquet")
    for col in BUS_COLS:
        dong[col] = bus[col].values
    return dong, store


def score_models(industry, target, dong, store, weights=BASELINE_WEIGHTS):
    feat, meta = build_dong_industry_features(industry, target, dong, store)
    for col in BUS_COLS:
        feat[col] = dong[col].values
    baseline = rank_locations(compute_total_score(calculate_component_scores(feat.copy()), weights))
    baseline["is_unentered"] = baseline["cat_store_count"].fillna(0).lt(1)
    baseline["market_status"] = np.where(
        ~baseline["is_unentered"], "기준선 분석 대상 지역", "해당 업종 점포 미확인 지역"
    )
    improved = rank_locations(calculate_enhanced_scores(
        feat.copy(), weights=weights, candidate="baseline", is_improved=True,
        min_stores=1, discount_factor=0.50,
    ))
    integrated = rank_locations(calculate_enhanced_scores(
        feat.copy(), weights=weights, candidate="candidate_b", is_improved=True,
        min_stores=1, discount_factor=0.50,
    ))
    return {"Baseline": baseline, "Improved": improved, "Integrated": integrated}, meta


def filtered(df):
    out = df.loc[~df["is_unentered"].astype(bool)].reset_index(drop=True)
    out["rank"] = np.arange(1, len(out) + 1)
    return out


def assert_finite(df):
    values = df.select_dtypes(include=[np.number]).to_numpy()
    assert not np.isnan(values).any()
    assert np.isfinite(values).all()


def flatten_explanation(exp):
    return " ".join([exp["summary_sentence"], *exp["strengths"], *exp["cautions"]])


def run():
    dong, store = load_inputs()
    passed = 0

    # 1-3. Baseline OFF/ON and lodging edge case.
    models, meta = score_models("숙박", "2030", dong, store)
    base = models["Baseline"]
    assert len(base) == 150 and base.iloc[0]["adm_nm"].endswith("감삼동")
    assert math.isclose(float(base.iloc[0]["total_score"]), 77.05, abs_tol=0.01)
    passed += 1
    base_on = filtered(base)
    assert len(base_on) == 127 and (base_on["cat_store_count"] >= 1).all()
    assert base_on["rank"].tolist() == list(range(1, 128))
    passed += 1
    assert not base_on["is_unentered"].any()
    passed += 1

    # 4-5. Improved and Integrated exclude paths.
    for name in ("Improved", "Integrated"):
        out = filtered(models[name])
        assert len(out) == 127 and not out["is_unentered"].any()
        assert out["rank"].tolist() == list(range(1, 128))
    passed += 2

    # 6. Cross-model output schema.
    for name, frame in models.items():
        assert REQUIRED <= set(frame.columns), (name, REQUIRED - set(frame.columns))
        assert frame[list(REQUIRED)].isna().sum().sum() == 0
    passed += 1

    # 7-8. Positive wording and 3 x 6 x Top5 explanation grounding smoke test.
    source_text = (ROOT / "src/recommendation/explain.py").read_text(encoding="utf-8")
    preset_text = (ROOT / "src/recommendation/personalization.py").read_text(encoding="utf-8")
    assert "일평균 유동인구" not in source_text
    assert "교통/유동인구 우선형" not in preset_text
    passed += 1
    explanation_count = 0
    generators = {
        "Baseline": generate_explanation,
        "Improved": generate_improved_explanation,
        "Integrated": generate_enhanced_explanation,
    }
    for industry, target in SCENARIOS:
        scenario_models, scenario_meta = score_models(industry, target, dong, store)
        for name, frame in scenario_models.items():
            for _, row in frame.head(5).iterrows():
                exp = generators[name](row, scenario_meta)
                text = flatten_explanation(exp)
                assert "유동인구" not in text
                assert exp["rank"] == int(row["rank"])
                assert math.isclose(exp["total_score"], float(row["total_score"]), abs_tol=1e-9)
                assert (
                    f"{row['total_score']:.1f}점" in exp["summary_sentence"]
                    or f"{row['total_score']:.2f}점" in exp["summary_sentence"]
                )
                explanation_count += 1
    assert explanation_count == 90
    passed += 1

    # 9. Real Streamlit model switching and checkbox state transition.
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(ROOT / "app/app.py"), default_timeout=45).run(timeout=45)
    assert len(at.exception) == 0
    sequence = [2, 1, 2, 0]
    for model_index in sequence:
        at.radio[0].set_value(at.radio[0].options[model_index])
        at.run(timeout=45)
        at.checkbox[0].set_value(True)
        at.run(timeout=45)
        assert len(at.exception) == 0
        at.checkbox[0].set_value(False)
        at.run(timeout=45)
        assert len(at.exception) == 0
    passed += 1

    # 10. Per-model UTF-8-SIG CSV export with active model rows and components.
    export_cols = ["rank", "adm_nm", "total_score", "demand_score", "target_fit_score",
                   "competition_score", "accessibility_score", "parking_score", "industry_fit_score"]
    for frame in models.values():
        payload = frame[export_cols].to_csv(index=False).encode("utf-8-sig")
        assert payload.startswith(codecs.BOM_UTF8)
        decoded = pd.read_csv(io.BytesIO(payload), encoding="utf-8-sig")
        assert len(decoded) == 150 and decoded.isna().sum().sum() == 0
    passed += 1

    # 11. NaN/Inf, all targets, presets and representative results.
    for preset in WEIGHT_PRESETS.values():
        normalized = validate_and_normalize_weights(preset)
        assert all(v >= 0 for v in normalized.values()) and math.isclose(sum(normalized.values()), 1.0)
    for target in ("전체", "2030", "4050", "60대", "10대"):
        target_models, _ = score_models("카페", target, dong, store)
        for frame in target_models.values():
            assert_finite(frame)
    checks = [
        ("카페", "2030", BASELINE_WEIGHTS, "Baseline", "신암4동", 77.93),
        ("한식", "전체", BASELINE_WEIGHTS, "Baseline", "진천동", 71.54),
        ("학원", "10대", BASELINE_WEIGHTS, "Baseline", "범어1동", 80.06),
        ("숙박", "2030", BASELINE_WEIGHTS, "Baseline", "감삼동", 77.05),
        ("카페", "2030", BASELINE_WEIGHTS, "Integrated", "신암4동", 77.75),
        ("학원", "10대", WEIGHT_PRESETS["타깃 고객 집중형 (트렌디/특화 소비)"], "Integrated", "범어1동", 84.40),
    ]
    for industry, target, weights, model, dong_name, expected in checks:
        frame = score_models(industry, target, dong, store, weights)[0][model]
        assert frame.iloc[0]["adm_nm"].endswith(dong_name)
        assert math.isclose(float(frame.iloc[0]["total_score"]), expected, abs_tol=0.05)
    passed += 1

    # 12. Final team name and no stale positive claims in current user-facing artifacts.
    user_files = [ROOT / "app/app.py", ROOT / "README.md"]
    package = ROOT / "submission/package/말괄량이코물이_대구소상공인_AI_입지추천"
    if package.exists():
        user_files += [package / "README.md", package / "README_JUDGE.md",
                       package / "docs/MODEL_CARD.md", package / "docs/DATA_SOURCES.md"]
    combined = "\n".join(p.read_text(encoding="utf-8") for p in user_files if p.exists())
    assert "상권ON AI" not in combined
    assert "관내 지하철 일평균 유동인구" not in combined
    passed += 1

    assert passed == 12
    print(f"PHASE 15: {passed}/{passed} PASS")
    print("Explanation grounding: 90/90, mismatch 0, hallucination 0")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if run() else 1)
