#!/usr/bin/env python3
"""
scripts/run_final_defect_closure_tests.py

Final Defect Closure & Explanation Deduplication Test Suite (T1 ~ T15)
Phase 26 Comprehensive Regression & Verification
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.recommendation.feature_builder import build_dong_industry_features
from src.recommendation.personalization import WEIGHT_PRESETS
from src.recommendation.ranking import rank_locations
from src.recommendation.scoring import (
    calculate_component_scores,
    compute_total_score,
    validate_discount_factor,
    validate_store_thresholds,
)
from src.recommendation.improved import calculate_improved_scores, generate_improved_explanation
from src.recommendation.transit_enhanced import (
    calculate_enhanced_scores,
    generate_enhanced_explanation,
)
from src.recommendation.explain import generate_explanation, build_canonical_explanation


def load_test_fixtures():
    base = ROOT / "data/processed"
    dong = pd.read_parquet(base / "feature_mart/commercial_feature_mart_dong.parquet")
    stores = pd.read_parquet(base / "feature_mart/store_spatial_features.parquet")
    bus = pd.read_parquet(base / "transit/bus/daegu_bus_dong_features.parquet")
    bus_cols = [
        "adm_cd2", "dong_bus_stop_count", "dong_daily_bus_boarding",
        "dong_daily_bus_alighting", "dong_daily_bus_total",
        "dong_bus_stop_density", "dong_bus_ridership_per_stop",
        "avg_dist_to_bus_m", "ratio_stores_in_bus_300m"
    ]
    merge_cols = [c for c in bus_cols if c == "adm_cd2" or c not in dong.columns]
    dong_merged = dong.merge(bus[merge_cols], on="adm_cd2", how="left")
    return dong_merged, stores, bus_cols


# ============================================================
# T1 ~ T15 Implementation
# ============================================================

def test_t01_card_click_session_state_preservation():
    """T1: Card click session state preservation & reload link removal."""
    app_text = (ROOT / "app/app.py").read_text(encoding="utf-8")
    assert '<a class="compact-rank-link" href="?selected_rank=' not in app_text, "Stale reload anchor links remain"
    assert "selected_detail_adm_cd2" in app_text, "Session state selected_detail_adm_cd2 not tracked"
    assert "btn_rank_select_" in app_text, "Streamlit button selection key missing"
    assert "st.rerun()" in app_text, "Native rerun for card selection missing"
    assert "_last_query_fingerprint" in app_text, "Query change fingerprint guard missing"


def test_t02_target_ratio_vs_absolute_pop_separation():
    """T2: Target ratio vs absolute population separation."""
    row = pd.Series({
        "adm_nm": "대구광역시 수성구 범어1동",
        "rank": 1,
        "total_score": 84.40,
        "target_fit_score": 80.0,
        "target_ratio": 0.15,
        "target_ratio_pct": 40.0,  # Below 65
        "target_pop": 8500,
        "target_pop_pct": 90.0,    # Above 65
        "cat_store_count": 50,
        "market_status": "해당 업종 점포 확인 지역",
    })
    meta = {"industry_label": "학원", "target_demographic_label": "10대 이하", "target_demographic": "10대"}
    exp = build_canonical_explanation(row, meta, model_type="enhanced")
    text = " ".join(exp["strengths"])
    assert "10대 이하 규모" in text, "High population evidence missing"
    assert "10대 이하 비중이" not in text, "Ratio claimed high despite ratio percentile < 65"


def test_t03_target_all_ratio_wording_prohibition():
    """T3: target == '전체' ratio wording prohibition."""
    row = pd.Series({
        "adm_nm": "대구광역시 달서구 상인1동",
        "rank": 1,
        "total_score": 77.47,
        "target_fit_score": 85.0,
        "target_ratio": 1.0,
        "target_pop": 31919,
        "pop_total": 31919,
        "cat_store_count": 100,
        "market_status": "해당 업종 점포 확인 지역",
    })
    meta = {"industry_label": "한식", "target_demographic_label": "전체 인구 (전연령)", "target_demographic": "전체"}
    for model_mode in ("baseline", "improved", "enhanced"):
        exp = build_canonical_explanation(row, meta, model_type=model_mode)
        text = " ".join([exp["summary_sentence"], *exp["strengths"], *exp["cautions"]])
        assert "전체 인구 비중" not in text, f"[{model_mode}] Prohibited ratio statement leaked"
        assert "인구 규모가 큰 편" in text, f"[{model_mode}] Population scale statement missing"


def test_t04_card_top3_reasons_neutral_for_under_70():
    """T4: Card top3 reasons use neutral phrasing for scores < 70."""
    app_text = (ROOT / "app/app.py").read_text(encoding="utf-8")
    assert "c_score >= 70.0" in app_text, "Score threshold 70 check missing in app.py"
    assert 'neutral_lbl = label.replace("우수", "상대 우위")' in app_text, "Neutral phrasing transformation missing"
    assert "{grade_text}" in app_text, "Grade text placeholder missing"
    assert "'매우 우수' if compact_rank == 1 else '우수'" not in app_text, "Arbitrary rank-based quality label remains"


def test_t05_active_model_transit_explanation_separation():
    """T5: Active model transit explanation separation (no bus in subway models)."""
    row = pd.Series({
        "adm_nm": "대구광역시 동구 신암4동",
        "rank": 1,
        "total_score": 75.0,
        "accessibility_score": 85.0,
        "cat_avg_subway_dist": 350.0,
        "dong_daily_ridership": 25000.0,
        "dong_daily_bus_total": 15000.0,
        "dong_bus_stop_count": 30,
        "avg_dist_to_bus_m": 120.0,
        "cat_store_count": 50,
        "market_status": "해당 업종 점포 확인 지역",
    })
    meta = {"industry_label": "카페", "target_demographic_label": "2030", "target_demographic": "2030"}

    # Baseline and Improved must NOT mention bus data
    exp_base = generate_explanation(row, meta)
    text_base = " ".join([exp_base["summary_sentence"], *exp_base["strengths"], *exp_base["cautions"]])
    assert "버스" not in text_base and "시내버스" not in text_base, "Bus mentioned in baseline explanation"

    exp_imp = generate_improved_explanation(row, meta)
    text_imp = " ".join([exp_imp["summary_sentence"], *exp_imp["strengths"], *exp_imp["cautions"]])
    assert "버스" not in text_imp and "시내버스" not in text_imp, "Bus mentioned in improved explanation"

    # Enhanced model CAN mention bus
    exp_enh = generate_enhanced_explanation(row, meta)
    text_enh = " ".join([exp_enh["summary_sentence"], *exp_enh["strengths"], *exp_enh["cautions"]])
    assert "버스" in text_enh or "시내버스" in text_enh, "Bus evidence missing in integrated explanation"


def test_t06_non_subway_terminology_replacement():
    """T6: Replace '비역세권' and '미경유' with neutral coordinate terminology."""
    code_files = ["app/app.py", "src/recommendation/explain.py", "src/recommendation/transit_enhanced.py"]
    for rel in code_files:
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "도시철도 미경유" not in text, f"Stale term '도시철도 미경유' found in {rel}"
        assert "관내 도시철도 역 좌표가 없는" in text or "관내 역 좌표가 없는" in text, f"Neutral term missing in {rel}"


def test_t07_baseline_model_name_consistency():
    """T7: Baseline model name accuracy and consistency."""
    app_text = (ROOT / "app/app.py").read_text(encoding="utf-8")
    assert 'MODEL_MODE_BASELINE = "도시철도 기준선 모델 (도시철도 중심 접근성)"' in app_text, "Accurate baseline model constant missing"


def test_t08_subway_station_layer_presence():
    """T8: Subway station map layer presence in app.py."""
    app_text = (ROOT / "app/app.py").read_text(encoding="utf-8")
    assert "FeatureGroup(name=\"도시철도역 (94개)\"" in app_text, "Subway FeatureGroup missing"
    assert "CircleMarker" in app_text, "Folium CircleMarker missing"
    assert "df_subway" in app_text, "Subway dataframe integration missing"


def test_t09_discount_factor_negative_validation():
    """T9: discount_factor negative validation across improved and enhanced."""
    df_dummy = pd.DataFrame({
        "pop_total": [1000], "pop_density": [100], "dong_daily_ridership": [500],
        "total_stores": [50], "target_ratio": [0.2], "target_pop": [200],
        "target_pop_per_store": [4], "cat_avg_comp_300m": [2], "cat_avg_subway_dist": [300],
        "cat_ratio_subway": [0.5], "cat_avg_parking_300m": [10], "parking_capacity_per_store": [1.5],
        "dong_total_parking_capacity": [1000], "location_quotient": [1.1], "cat_store_count": [5],
        "dong_daily_bus_total": [300], "avg_dist_to_bus_m": [150], "dong_bus_stop_density": [10]
    })
    for bad_df in [-0.5, 1.5, float("nan"), float("inf"), -float("inf"), "invalid"]:
        for fn in (calculate_improved_scores, calculate_enhanced_scores):
            try:
                fn(df_dummy, discount_factor=bad_df)
                assert False, f"{fn.__name__} did not raise ValueError for discount_factor={bad_df}"
            except ValueError:
                pass


def test_t10_min_stores_negative_validation():
    """T10: min_stores and min_total_stores negative validation."""
    df_dummy = pd.DataFrame({
        "pop_total": [1000], "pop_density": [100], "dong_daily_ridership": [500],
        "total_stores": [50], "target_ratio": [0.2], "target_pop": [200],
        "target_pop_per_store": [4], "cat_avg_comp_300m": [2], "cat_avg_subway_dist": [300],
        "cat_ratio_subway": [0.5], "cat_avg_parking_300m": [10], "parking_capacity_per_store": [1.5],
        "dong_total_parking_capacity": [1000], "location_quotient": [1.1], "cat_store_count": [5],
        "dong_daily_bus_total": [300], "avg_dist_to_bus_m": [150], "dong_bus_stop_density": [10]
    })
    for bad in [-1, 1.5, "bad"]:
        for fn in (calculate_improved_scores, calculate_enhanced_scores):
            try:
                fn(df_dummy, min_stores=bad)
                assert False, f"{fn.__name__} did not raise ValueError for min_stores={bad}"
            except ValueError:
                pass
            try:
                fn(df_dummy, min_total_stores=bad)
                assert False, f"{fn.__name__} did not raise ValueError for min_total_stores={bad}"
            except ValueError:
                pass


def test_t11_artifact_validation_semantics_separation():
    """T11: Validate artifact semantics separation."""
    script = ROOT / "scripts/validate_release_artifacts.py"
    res = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
    assert res.returncode == 0, "Default validator invocation failed"
    assert "Source Contract: PASS" in res.stdout, "Source contract pass missing"
    assert "NOT VERIFIED" in res.stdout, "Release artifact not verified status missing"

    # Negative test with non-existent file
    res_bad = subprocess.run([sys.executable, str(script), "--pdf-path", "missing.pdf"], capture_output=True, text=True)
    assert res_bad.returncode != 0, "Missing PDF should fail"
    assert "FAIL" in res_bad.stdout, "Missing PDF fail message missing"


def test_t12_build_path_normalization_temp_directory():
    """T12: package_phase22.py uses tempfile and avoids hardcoded /tmp."""
    pkg_text = (ROOT / "scripts/package_phase22.py").read_text(encoding="utf-8")
    assert "tempfile.TemporaryDirectory" in pkg_text, "tempfile.TemporaryDirectory missing"
    assert 'STAGE_PARENT = Path("/tmp/daegu_phase22_package")' not in pkg_text, "Hardcoded /tmp path remains"


def test_t13_build_path_normalization_screenshots_source():
    """T13: Canonical screenshots path used in packaging and PDF scripts."""
    pkg_text = (ROOT / "scripts/package_phase22.py").read_text(encoding="utf-8")
    pdf_text = (ROOT / "scripts/build_phase22_proposal_pdf.py").read_text(encoding="utf-8")
    assert 'screenshots' in pkg_text, "Canonical screenshots directory missing in packager"
    assert 'ROOT / "screenshots"' in pdf_text, "Canonical screenshots directory missing in PDF builder"
    assert "find_korean_font" in pdf_text, "Font discovery resolver missing in PDF builder"


def test_t14_official_demo_values_invariance():
    """T14: Invariance of all 6 official demo Top1 / Top5 ranking and scores."""
    dong, stores, bus_cols = load_test_fixtures()
    expected = [
        ("카페", "2030", "기본 균형형", "신암4동", 77.75),
        ("한식", "전체", "배후 수요 집중형 (대형 매장/안정형)", "상인1동", 77.47),
        ("미용실", "2030", "기본 균형형", "칠성동", 75.45),
        ("학원", "10대", "타깃 고객 집중형 (트렌디/특화 소비)", "범어1동", 84.40),
        ("종합소매", "전체", "기본 균형형", "상인1동", 72.25),
        ("숙박", "2030", "기본 균형형", "칠성동", 75.90),
    ]

    for ind, tgt, preset, exp_dong, exp_score in expected:
        feat, meta = build_dong_industry_features(ind, tgt, dong, stores)
        for col in bus_cols:
            if col in dong.columns and col != "adm_cd2":
                feat[col] = dong[col].values
        weights = WEIGHT_PRESETS[preset]
        ranked = rank_locations(calculate_enhanced_scores(feat, weights=weights, candidate="candidate_b", discount_factor=0.50))
        top = ranked.iloc[0]
        actual_dong = top["adm_nm"].split()[-1]
        actual_score = float(top["total_score"])
        assert actual_dong == exp_dong, f"[{ind}+{tgt}] Expected top dong {exp_dong}, got {actual_dong}"
        assert abs(actual_score - exp_score) < 0.01, f"[{ind}+{tgt}] Expected score {exp_score}, got {actual_score}"


def test_t15_explanation_deduplication_canonical_helper():
    """T15: Public explanation functions delegate to build_canonical_explanation."""
    imp_text = (ROOT / "src/recommendation/improved.py").read_text(encoding="utf-8")
    enh_text = (ROOT / "src/recommendation/transit_enhanced.py").read_text(encoding="utf-8")
    exp_text = (ROOT / "src/recommendation/explain.py").read_text(encoding="utf-8")

    assert "build_canonical_explanation" in exp_text, "Canonical explanation engine missing in explain.py"
    assert "return build_canonical_explanation(row, metadata, model_type=\"improved\")" in imp_text, "Delegation missing in improved.py"
    assert "return build_canonical_explanation(row, metadata, model_type=\"enhanced\")" in enh_text, "Delegation missing in transit_enhanced.py"
    assert "return build_canonical_explanation(row, metadata, model_type=\"baseline\")" in exp_text, "Delegation missing in explain.py"


def main():
    test_functions = [
        test_t01_card_click_session_state_preservation,
        test_t02_target_ratio_vs_absolute_pop_separation,
        test_t03_target_all_ratio_wording_prohibition,
        test_t04_card_top3_reasons_neutral_for_under_70,
        test_t05_active_model_transit_explanation_separation,
        test_t06_non_subway_terminology_replacement,
        test_t07_baseline_model_name_consistency,
        test_t08_subway_station_layer_presence,
        test_t09_discount_factor_negative_validation,
        test_t10_min_stores_negative_validation,
        test_t11_artifact_validation_semantics_separation,
        test_t12_build_path_normalization_temp_directory,
        test_t13_build_path_normalization_screenshots_source,
        test_t14_official_demo_values_invariance,
        test_t15_explanation_deduplication_canonical_helper,
    ]

    passed = 0
    total = len(test_functions)
    print("==================================================")
    print("Running Final Defect Closure Regression Suite (T1 ~ T15)")
    print("==================================================")
    for idx, fn in enumerate(test_functions, 1):
        try:
            fn()
            print(f"[PASS] T{idx:02d}: {fn.__name__}")
            passed += 1
        except Exception as exc:
            print(f"[FAIL] T{idx:02d}: {fn.__name__} -> {exc}")
            raise

    print("==================================================")
    print(f"FINAL DEFECT CLOSURE SUITE: {passed}/{total} PASS")
    print("==================================================")


if __name__ == "__main__":
    main()
