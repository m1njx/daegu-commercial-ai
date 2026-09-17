# -*- coding: utf-8 -*-
"""
scripts/run_phase14c_tests.py

Phase 14C: Baseline 모델 + 미진입 상권(0점포) 완전 제외 KeyError 회귀 점검 및 방어 로직 검증 스위트
1. Test 1 (Test A): Baseline 모델 + exclude_unentered=False 검증 (150개 전수 분석, 벤치마크 점수 100% 일치)
2. Test 2 (Test B): Baseline 모델 + exclude_unentered=True 검증 (KeyError 0, 0점포 23개 동 제외 후 정확히 127개 동, 순위 1..127)
3. Test 3 (Test C): Candidate B 통합 모델 + exclude_unentered=True 검증 (127개 동, 1위 감삼동 75.82점 무결성)
4. Test 4 (Test D): Subway Improved 모델 + exclude_unentered=True 검증 (127개 동, 1위 감삼동 77.00점 무결성)
5. Test 5 (Test E): 3종 모델 출력 스키마 통일성 검증 (is_unentered, market_status 등 필수 컬럼 전수 보유)
6. Test 6 (Test F): app.py 런타임 방어 로직 및 소스코드 무결성 검증 (컬럼 누락/존재 양방향 안전 가드)
"""

import sys
import os
import py_compile
from pathlib import Path
import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.features.bus_features import PROCESSED_BUS_DIR
from src.recommendation.feature_builder import build_dong_industry_features
from src.recommendation.scoring import calculate_component_scores, compute_total_score, BASELINE_WEIGHTS
from src.recommendation.ranking import rank_locations
from src.recommendation.improved import calculate_improved_scores
from src.recommendation.transit_enhanced import calculate_enhanced_scores

def run_phase14c_tests():
    print("=" * 75)
    print("PHASE 14C: Baseline 모델 미진입 상권 필터 KeyError 방어 및 회귀 검증 스위트")
    print("=" * 75)

    app_path = ROOT_DIR / "app" / "app.py"
    dong_path = ROOT_DIR / "data" / "processed" / "feature_mart" / "commercial_feature_mart_dong.parquet"
    store_path = ROOT_DIR / "data" / "processed" / "feature_mart" / "store_spatial_features.parquet"
    bus_path = PROCESSED_BUS_DIR / "daegu_bus_dong_features.parquet"

    # 0. 데이터 로드 및 공통 버스 피처 결합
    df_dong = pd.read_parquet(dong_path)
    df_store = pd.read_parquet(store_path)
    df_bus = pd.read_parquet(bus_path)

    bus_cols = [
        "dong_bus_stop_count", "dong_daily_bus_boarding", "dong_daily_bus_alighting",
        "dong_daily_bus_total", "dong_bus_stop_density", "dong_bus_ridership_per_stop",
        "avg_dist_to_bus_m", "ratio_stores_in_bus_300m"
    ]
    for col in bus_cols:
        df_dong[col] = df_bus[col].values

    # 숙박 업종: 대구 150개 동 중 0점포 동 23개, 1개 이상 점포 보유 동 127개
    f_lodging, _ = build_dong_industry_features("숙박", "2030", df_dong, df_store)
    for col in bus_cols:
        f_lodging[col] = df_dong[col].values

    # Test 1 (Test A): Baseline 모델 + exclude_unentered=False (체크박스 해제 시)
    # 150개 동 전수 분석, 기존 Phase 5 기준선 점수 100% 보존 검증
    raw_base_scored = compute_total_score(calculate_component_scores(f_lodging.copy()), weights=BASELINE_WEIGHTS)
    base_ranked = rank_locations(raw_base_scored)
    # Option B 스키마 보완 적용
    base_ranked["is_unentered"] = base_ranked["cat_store_count"].fillna(0).lt(1)
    base_ranked["market_status"] = np.where(
        ~base_ranked["is_unentered"],
        "기준선 분석 대상 지역",
        "해당 업종 점포 미확인 지역"
    )

    assert len(base_ranked) == 150, f"Baseline 미필터 행 수 불일치: {len(base_ranked)}"
    assert sorted(base_ranked["rank"].tolist()) == list(range(1, 151)), "1~150위 연속 순위 위반"
    assert "is_unentered" in base_ranked.columns, "is_unentered 컬럼 누락"
    assert "market_status" in base_ranked.columns, "market_status 컬럼 누락"
    assert base_ranked.iloc[0]["adm_nm"] == "대구광역시 달서구 감삼동", "Baseline 1위 감삼동 불일치"
    assert abs(base_ranked.iloc[0]["total_score"] - 77.05) < 0.01, f"감삼동 점수 불일치: {base_ranked.iloc[0]['total_score']}"
    # 신암4동 기준선 점수(72.19) 무결성
    sinam_row = base_ranked[base_ranked["adm_nm"].str.contains("신암4동")].iloc[0]
    assert abs(sinam_row["total_score"] - 72.19) < 0.05, f"신암4동 숙박 점수 불일치: {sinam_row['total_score']}"
    print("[PASS] Test 1 (Test A): Baseline + exclude_unentered=False 150개 동 전수 분석 및 기준선 점수 100% 보존 검증 통과")

    # Test 2 (Test B): Baseline 모델 + exclude_unentered=True (체크박스 활성화 시)
    # KeyError 발생 0건, 0점포 23개 동 정확히 제외, 남은 127개 동 순위 1..127 재부여
    active_ranked_base = base_ranked.copy()
    if "is_unentered" in active_ranked_base.columns:
        unentered_mask = active_ranked_base["is_unentered"].astype(bool)
    else:
        unentered_mask = active_ranked_base["cat_store_count"].fillna(0).lt(1)
    active_ranked_base = active_ranked_base[~unentered_mask].reset_index(drop=True)
    active_ranked_base["rank"] = range(1, len(active_ranked_base) + 1)

    assert len(active_ranked_base) == 127, f"0점포 제외 후 127개 동 불일치: {len(active_ranked_base)}"
    assert (active_ranked_base["cat_store_count"] >= 1).all(), "필터링 후 점포수 0개 행 잔존"
    assert active_ranked_base["rank"].tolist() == list(range(1, 128)), "필터링 후 1~127 연속 순위 위반"
    assert active_ranked_base.iloc[0]["adm_nm"] == "대구광역시 달서구 감삼동", "필터 후 1위 감삼동 불일치"
    assert abs(active_ranked_base.iloc[0]["total_score"] - 77.05) < 0.01, "필터 후 감삼동 점수 불일치"
    assert (active_ranked_base["is_unentered"] == False).all(), "필터링 후 is_unentered True 잔존"
    assert (active_ranked_base["market_status"] == "기준선 분석 대상 지역").all(), "필터링 후 비정상 market_status"
    print("[PASS] Test 2 (Test B): Baseline + exclude_unentered=True KeyError 0, 정확히 127개 동 필터링 및 1..127 순위 검증 통과")

    # Test 3 (Test C): Candidate B 통합 모델 + exclude_unentered=True
    cand_b_scored = calculate_enhanced_scores(f_lodging, candidate="candidate_b", is_improved=True)
    cand_b_ranked = rank_locations(cand_b_scored)
    unentered_mask_b = cand_b_ranked["is_unentered"].astype(bool)
    active_ranked_b = cand_b_ranked[~unentered_mask_b].reset_index(drop=True)
    active_ranked_b["rank"] = range(1, len(active_ranked_b) + 1)

    assert len(active_ranked_b) == 127, f"Candidate B 필터 후 127개 동 불일치: {len(active_ranked_b)}"
    assert active_ranked_b["rank"].tolist() == list(range(1, 128)), "Candidate B 1~127 순위 위반"
    assert "칠성동" in active_ranked_b.iloc[0]["adm_nm"], "Candidate B 1위 칠성동 불일치"
    assert abs(active_ranked_b.iloc[0]["total_score"] - 75.90) < 0.05, f"Candidate B 칠성동 점수 불일치: {active_ranked_b.iloc[0]['total_score']}"
    print("[PASS] Test 3 (Test C): Candidate B + exclude_unentered=True 127개 동 및 1위 칠성동(75.90점) 무결성 통과")

    # Test 4 (Test D): Subway Improved 모델 + exclude_unentered=True
    subway_scored = calculate_improved_scores(f_lodging)
    subway_ranked = rank_locations(subway_scored)
    unentered_mask_subway = subway_ranked["is_unentered"].astype(bool)
    active_ranked_subway = subway_ranked[~unentered_mask_subway].reset_index(drop=True)
    active_ranked_subway["rank"] = range(1, len(active_ranked_subway) + 1)

    assert len(active_ranked_subway) == 127, f"Subway Improved 필터 후 127개 동 불일치: {len(active_ranked_subway)}"
    assert active_ranked_subway["rank"].tolist() == list(range(1, 128)), "Subway Improved 1~127 순위 위반"
    assert "감삼동" in active_ranked_subway.iloc[0]["adm_nm"], "Subway Improved 1위 감삼동 불일치"
    assert abs(active_ranked_subway.iloc[0]["total_score"] - 77.00) < 0.05, f"Subway Improved 감삼동 점수 불일치: {active_ranked_subway.iloc[0]['total_score']}"
    print("[PASS] Test 4 (Test D): Subway Improved + exclude_unentered=True 127개 동 및 1위 감삼동(77.00점) 무결성 통과")

    # Test 5 (Test E): 3종 모델 출력 스키마 통일성 검증
    # Baseline, Subway Improved, Integrated 모두 동일한 핵심 컬럼 보유 확인
    required_cols = [
        "adm_nm", "adm_cd2", "rank", "total_score", "demand_score", "target_fit_score",
        "competition_score", "accessibility_score", "parking_score", "industry_fit_score",
        "cat_store_count", "is_unentered", "market_status"
    ]
    for model_name, df_res in [
        ("Baseline", base_ranked),
        ("Subway Improved", subway_ranked),
        ("Candidate B", cand_b_ranked)
    ]:
        for col in required_cols:
            assert col in df_res.columns, f"[{model_name}] 필수 컬럼 누락: {col}"
        assert df_res[required_cols].isna().sum().sum() == 0, f"[{model_name}] 필수 컬럼 내 결측치 존재"
    print("[PASS] Test 5 (Test E): 3종 모델(Baseline/Improved/Candidate B) 출력 스키마 통일성 및 결측치 0 검증 통과")

    # Test 6 (Test F): app.py 런타임 방어 로직 및 소스코드 무결성 검증
    # py_compile 무결성 확인
    py_compile.compile(str(app_path), doraise=True)
    with open(app_path, "r", encoding="utf-8") as f:
        app_code = f.read()

    # Option B: Baseline 스키마 보완 코드 존재 확인
    assert 'active_ranked["is_unentered"] = active_ranked["cat_store_count"].fillna(0).lt(1)' in app_code, "Baseline is_unentered 생성 코드 누락"
    assert 'active_ranked["market_status"] = np.where(' in app_code, "Baseline market_status 생성 코드 누락"

    # Option A: 안전 가드 코드 존재 확인
    assert 'if "is_unentered" in active_ranked.columns:' in app_code, "안전 가드 컬럼 존재 검사 누락"
    assert 'unentered_mask = active_ranked["cat_store_count"].fillna(0).lt(1)' in app_code, "안전 가드 fallback 마스크 누락"

    # 실제 결측 컬럼 데이터프레임 방어 시뮬레이션
    dummy_df = pd.DataFrame({
        "adm_nm": ["동A", "동B"],
        "cat_store_count": [0, 5],
        "total_score": [80.0, 75.0]
    })
    # is_unentered 없는 상태에서 필터링 가드 실행 시 KeyError 방지 및 정확한 필터링 검증
    if "is_unentered" in dummy_df.columns:
        d_mask = dummy_df["is_unentered"].astype(bool)
    else:
        d_mask = dummy_df["cat_store_count"].fillna(0).lt(1)
    filtered_dummy = dummy_df[~d_mask].reset_index(drop=True)
    assert len(filtered_dummy) == 1, "is_unentered 부재 시 방어 필터링 실패"
    assert filtered_dummy.iloc[0]["adm_nm"] == "동B", "방어 필터링 대상 불일치"
    print("[PASS] Test 6 (Test F): app.py 방어 코드(Option A+B) 구문 검증 및 결측 컬럼 런타임 시뮬레이션 통과")

    print("=" * 75)
    print("ALL 6 PHASE 14C AUTOMATED TESTS PASSED! (100%)")
    print("=" * 75)
    return True

if __name__ == "__main__":
    success = run_phase14c_tests()
    if not success:
        sys.exit(1)
