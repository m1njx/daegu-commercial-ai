#!/usr/bin/env python3
"""Phase 20 data allocation, UI state, and contract regression suite."""

from __future__ import annotations

import ast
import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.features.bus_features import TOTAL_PERIOD_DAYS_2026, load_and_clean_bus_data
from src.recommendation.feature_builder import build_dong_industry_features
from src.recommendation.personalization import WEIGHT_PRESETS
from src.recommendation.ranking import rank_locations
from src.recommendation.transit_enhanced import calculate_enhanced_scores

BUS_COLS = [
    "dong_bus_stop_count", "dong_daily_bus_boarding", "dong_daily_bus_alighting",
    "dong_daily_bus_total", "dong_bus_stop_density", "dong_bus_ridership_per_stop",
    "avg_dist_to_bus_m", "ratio_stores_in_bus_300m",
]
REMOTE_COLLISIONS = {"달산1리", "달산2리", "수서2리"}
CLOSE_BOUNDARY_PAIRS = {"화계2리", "화전리"}
DEMO_EXPECTED = (
    ("카페", "2030", "기본 균형형", "신암4동", 77.75),
    ("한식", "전체", "배후 수요 집중형 (대형 매장/안정형)", "상인1동", 77.47),
    ("미용실", "2030", "기본 균형형", "칠성동", 75.45),
    ("학원", "10대", "타깃 고객 집중형 (트렌디/특화 소비)", "범어1동", 84.47),
    ("종합소매", "전체", "기본 균형형", "상인1동", 72.22),
    ("숙박", "2030", "기본 균형형", "감삼동", 75.82),
)


def function_source(text: str, name: str) -> str:
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(text, node) or ""
    raise AssertionError(f"function not found: {name}")


def main() -> None:
    app_text = (ROOT / "app/app.py").read_text(encoding="utf-8")
    stops = pd.read_parquet(ROOT / "data/processed/transit/bus/daegu_bus_stops_processed.parquet")
    dongs = pd.read_parquet(ROOT / "data/processed/transit/bus/daegu_bus_dong_features.parquet")
    mart = pd.read_parquet(ROOT / "data/processed/feature_mart/commercial_feature_mart_dong.parquet")
    stores = pd.read_parquet(ROOT / "data/processed/feature_mart/store_spatial_features.parquet")
    _, raw_ridership, metadata = load_and_clean_bus_data()
    passed = 0

    # 1. Known distant homonyms are separate physical clusters.
    for name in REMOTE_COLLISIONS:
        group = stops[stops["정류소명"] == name]
        assert group["stop_cluster_id"].nunique() > 1
        assert group.groupby("stop_cluster_id")["adm_cd2"].nunique().max() == 1
    passed += 1

    # 2. Nearby boundary pairs remain one cluster, preserving paired-pole intent.
    for name in CLOSE_BOUNDARY_PAIRS:
        assert stops.loc[stops["정류소명"] == name, "stop_cluster_id"].nunique() == 1
    passed += 1

    # 3. Spatial allocation preserves every matched raw trip exactly (floating tolerance).
    expected_daily = metadata["matched_ridership_volume"] / TOTAL_PERIOD_DAYS_2026
    assert math.isclose(stops["pole_daily_total"].sum(), expected_daily, abs_tol=1e-8)
    assert math.isclose(dongs["dong_daily_bus_total"].sum(), expected_daily, abs_tol=1e-8)
    passed += 1

    # 4. Each name's total is split equally across clusters, then across poles.
    for name in REMOTE_COLLISIONS:
        group = stops[stops["정류소명"] == name]
        totals = group.groupby("stop_cluster_id")["pole_daily_total"].sum()
        assert totals.max() - totals.min() < 1e-10
    passed += 1

    # 5. Every processed stop belongs to one auditable spatial cluster.
    assert len(stops) == 3981 and stops["stop_cluster_id"].notna().all()
    assert (stops["cluster_pole_count"] >= 1).all() and (stops["cluster_count"] >= 1).all()
    passed += 1

    # 6. Detail selector is backed by the unfiltered 150-dong model result.
    assert "detail_ranked = active_ranked.copy()" in app_text
    assert 'remaining_adm_list = [name for name in detail_ranked["adm_nm"].tolist()' in app_text
    assert 'target_row = detail_ranked[detail_ranked["adm_nm"] == chosen_dong].iloc[0]' in app_text
    passed += 1

    # 7. Model comparison labels and explanatory bullet order are integrated-first.
    comparison = "⚖️ 통합 대중교통 모델 vs 도시철도 중심 개선 모델"
    assert comparison in app_text and "⚖️ 도시철도 중심 개선 모델 vs 통합 대중교통 모델" not in app_text
    section = app_text[app_text.index("# TAB 3:"):app_text.index("df_compare =")]
    assert section.index("통합 대중교통 모델 (권장)") < section.index("도시철도 중심 개선 모델**")
    passed += 1

    # 8-9. Demo callback resets both advanced-state controls to canonical values.
    callback = function_source(app_text, "apply_demo_scenario")
    assert "st.session_state.discount_factor = 0.50" in callback
    passed += 1
    assert "st.session_state.filter_unentered = False" in callback
    passed += 1

    # 10. All six canonical demos reproduce after arbitrary advanced state.
    for col in BUS_COLS:
        mart[col] = dongs[col].values
    for industry, target, preset, expected_dong, expected_score in DEMO_EXPECTED:
        feat, _ = build_dong_industry_features(industry, target, mart, stores)
        for col in BUS_COLS:
            feat[col] = mart[col].values
        result = rank_locations(calculate_enhanced_scores(
            feat, weights=WEIGHT_PRESETS[preset], candidate="candidate_b",
            is_improved=True, discount_factor=0.50,
        ))
        assert result.iloc[0]["adm_nm"].endswith(expected_dong)
        assert math.isclose(float(result.iloc[0]["total_score"]), expected_score, abs_tol=0.06)
    passed += 1

    # 11. A bus-weighted model fails explicitly when any required bus feature is absent.
    sample = pd.DataFrame({
        "cat_avg_subway_dist": [100.0, 200.0], "cat_ratio_subway": [0.5, 0.2],
        "dong_daily_ridership": [10.0, 20.0],
    })
    try:
        from src.recommendation.transit_enhanced import calculate_enhanced_transit_accessibility
        calculate_enhanced_transit_accessibility(sample, candidate="candidate_b")
        raise AssertionError("missing bus features were silently accepted")
    except ValueError as exc:
        assert "필수 버스 피처" in str(exc)
    passed += 1

    # 12. Ranking contract distinguishes None from invalid non-positive limits.
    ranked_input = pd.DataFrame({
        "total_score": [2.0], "demand_score": [1.0], "target_fit_score": [1.0],
        "pop_total": [1], "adm_nm": ["x"], "signgu_nm": ["x"], "adm_cd2": ["1"],
        "competition_score": [1.0], "accessibility_score": [1.0],
        "parking_score": [1.0], "industry_fit_score": [1.0],
    })
    assert len(rank_locations(ranked_input, top_n=None)) == 1
    for invalid in (0, -1):
        try:
            rank_locations(ranked_input, top_n=invalid)
            raise AssertionError("invalid top_n was silently accepted")
        except ValueError:
            pass
    passed += 1

    # 13. Plotly is neither imported nor claimed in current judge-facing text.
    judge_text = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in ("README.md", "README_JUDGE.md", "docs/MODEL_CARD.md")
    )
    python_sources = [p for p in ROOT.rglob("*.py") if p.name != Path(__file__).name]
    assert "import plotly" not in "\n".join(p.read_text(encoding="utf-8") for p in python_sources)
    assert "Plotly" not in judge_text
    passed += 1

    # 14. The raw matched total used above is independently derived from source rows.
    loc_names = set(stops["정류소명"])
    independently_matched = raw_ridership.loc[raw_ridership["정류소명"].isin(loc_names), "합계"].sum()
    assert independently_matched == metadata["matched_ridership_volume"]
    passed += 1

    assert passed == 14
    print("PHASE 20: 14/14 PASS")


if __name__ == "__main__":
    main()
