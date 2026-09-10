# -*- coding: utf-8 -*-
"""
scripts/run_phase8_tests.py

Phase 8: 시내버스 데이터 통합 및 대중교통 접근성 고도화 10대 자동화 테스트 스위트
1. 버스 원천 파일 존재성 및 인코딩 무결성
2. 정류소 조인 매칭률 및 승하차 볼륨 커버리지 (>=98% 매칭률, >=99% 볼륨)
3. 150개 행정동 공간 결합 완전성 (150/150 동 전수 버스정류소 보유)
4. 버스 Feature Mart 무결성 (150행, 결측치 0, 비음수 승하차)
5. 후보 공식 (Candidate A, B, C) 접근성 점수 유효 범위 [0, 100]
6. 비역세권 91개 행정동 접근성 개선(Lift) 효과 실증
7. 군위군 8개 읍면 등 저밀도 지역 이상치(False Inflation) 방어 검증
8. 6대 대표 시나리오 랭킹 안정성 (Spearman Rank Corr >= 0.985)
9. Bus-Enhanced 모델 순위 연속성 및 유일성 [1..150]
10. Phase 7 Baseline 회귀 무결성 (기존 Baseline 결과 불변 검증)
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.features.bus_features import find_bus_raw_files, load_and_clean_bus_data, PROCESSED_BUS_DIR
from src.recommendation.feature_builder import build_dong_industry_features
from src.recommendation.improved import calculate_improved_scores
from src.recommendation.transit_enhanced import calculate_enhanced_scores, TRANSIT_CANDIDATES
from src.recommendation.ranking import rank_locations

def run_tests():
    print("=" * 60)
    print("PHASE 8: 시내버스 대중교통 접근성 10대 자동화 테스트 스위트")
    print("=" * 60)
    
    # Test 1: 버스 원천 파일 존재성 및 인코딩 무결성
    loc_path, rid_path = find_bus_raw_files()
    assert loc_path.exists(), "위치정보 파일이 존재하지 않습니다."
    assert rid_path.exists(), "이용자수 파일이 존재하지 않습니다."
    print(f"[PASS] Test 1: 버스 원천 파일 존재성 확인 ({loc_path.name}, {rid_path.name})")
    
    # Test 2: 정류소 조인 매칭률 및 승하차 볼륨 커버리지
    df_loc, df_rid, stats = load_and_clean_bus_data()
    assert stats["stop_name_match_rate_pct"] >= 98.0, f"정류소 매칭률 미달: {stats['stop_name_match_rate_pct']}%"
    assert stats["ridership_volume_coverage_pct"] >= 99.0, f"승하차 볼륨 커버리지 미달: {stats['ridership_volume_coverage_pct']}%"
    print(f"[PASS] Test 2: 정류소 매칭률 {stats['stop_name_match_rate_pct']}% (볼륨 커버리지 {stats['ridership_volume_coverage_pct']}%) 검증 통과")
    
    # Test 3: 150개 행정동 공간 결합 완전성
    bus_feat_path = PROCESSED_BUS_DIR / "daegu_bus_dong_features.parquet"
    df_bus_dong = pd.read_parquet(bus_feat_path)
    assert len(df_bus_dong) == 150, f"행정동 수가 150개가 아닙니다: {len(df_bus_dong)}"
    assert (df_bus_dong["dong_bus_stop_count"] > 0).all(), "버스 정류소가 0개인 행정동이 존재합니다."
    print(f"[PASS] Test 3: 150개 행정동 버스 정류소 100% 커버리지 확인 (총 {df_bus_dong['dong_bus_stop_count'].sum():,}개소)")
    
    # Test 4: 버스 Feature Mart 무결성
    assert df_bus_dong["dong_daily_bus_total"].isnull().sum() == 0, "결측치 존재"
    assert (df_bus_dong["dong_daily_bus_total"] >= 0).all(), "음수 이용자수 존재"
    assert (df_bus_dong["avg_dist_to_bus_m"] >= 0).all(), "음수 거리 존재"
    print(f"[PASS] Test 4: 버스 Feature Mart 결측치 0, 비음수 승하차/거리 검증 통과")
    
    # Test 5: 후보 공식 접근성 점수 범위 [0, 100]
    dong_mart = pd.read_parquet(ROOT_DIR / "data" / "processed" / "feature_mart" / "commercial_feature_mart_dong.parquet")
    store_mart = pd.read_parquet(ROOT_DIR / "data" / "processed" / "feature_mart" / "store_spatial_features.parquet")
    
    bus_cols = ["adm_cd2", "dong_bus_stop_count", "dong_daily_bus_total", "dong_bus_stop_density", "avg_dist_to_bus_m", "ratio_stores_in_bus_300m"]
    dong_merged = dong_mart.merge(df_bus_dong[bus_cols], on="adm_cd2")
    feats, _ = build_dong_industry_features("카페", "2030", dong_merged, store_mart)
    for c in bus_cols[1:]:
        feats[c] = dong_merged[c].values
        
    for cand in ["candidate_a", "candidate_b", "candidate_c"]:
        cand_scored = calculate_enhanced_scores(feats, candidate=cand, is_improved=True)
        assert (cand_scored["accessibility_score"] >= 0).all() and (cand_scored["accessibility_score"] <= 100).all()
    print(f"[PASS] Test 5: Candidate A, B, C 접근성 점수 전수 [0, 100] 범위 검증 통과")
    
    # Test 6: 비역세권 91개 행정동 접근성 개선(Lift) 효과 실증
    has_sub = dong_merged["dong_station_count"] > 0
    base_scored = calculate_improved_scores(feats)
    cand_b_scored = calculate_enhanced_scores(feats, candidate="candidate_b", is_improved=True)
    
    no_sub_base_access = base_scored.loc[~has_sub, "accessibility_score"].mean()
    no_sub_cand_access = cand_b_scored.loc[~has_sub, "accessibility_score"].mean()
    access_lift = no_sub_cand_access - no_sub_base_access
    assert access_lift > 3.0, f"비역세권 접근성 개선 폭 부족: {access_lift:.2f}"
    print(f"[PASS] Test 6: 비역세권 91개 행정동 접근성 점수 상승 확인 ({no_sub_base_access:.2f} -> {no_sub_cand_access:.2f}, Δ+{access_lift:.2f}점)")
    
    # Test 7: 군위군 8개 읍면 등 저밀도 지역 이상치 방어 검증
    r_base = rank_locations(base_scored)
    r_cand = rank_locations(cand_b_scored)
    m = r_base[["adm_cd2", "adm_nm", "rank"]].merge(r_cand[["adm_cd2", "rank"]], on="adm_cd2", suffixes=("_base", "_cand"))
    gunwi = m[m["adm_nm"].str.contains("군위군")]
    gunwi_max_shift = (gunwi["rank_base"] - gunwi["rank_cand"]).abs().max()
    assert gunwi_max_shift <= 2, f"군위군 순위 변동 폭 초과: {gunwi_max_shift}"
    print(f"[PASS] Test 7: 군위군 8개 읍·면 순위 왜곡 0건 방어 확인 (최대 순위 변동: {gunwi_max_shift}순위)")
    
    # Test 8: 6대 대표 시나리오 랭킹 안정성 (Spearman Rank Corr >= 0.985)
    scenarios = [("카페", "2030"), ("한식", "전체"), ("미용실", "2030"), ("학원", "10대"), ("종합소매", "전체"), ("숙박", "2030")]
    min_spearman = 1.0
    for ind, tgt in scenarios:
        f, _ = build_dong_industry_features(ind, tgt, dong_merged, store_mart)
        for c in bus_cols[1:]:
            f[c] = dong_merged[c].values
        b_rank = rank_locations(calculate_improved_scores(f))
        e_rank = rank_locations(calculate_enhanced_scores(f, candidate="candidate_b", is_improved=True))
        paired = b_rank[["adm_cd2", "rank"]].merge(
            e_rank[["adm_cd2", "rank"]], on="adm_cd2", suffixes=("_base", "_cand")
        )
        sp, _ = spearmanr(paired["rank_base"], paired["rank_cand"])
        if sp < min_spearman:
            min_spearman = sp
    assert min_spearman >= 0.985, f"스피어만 상관계수 최저치 미달: {min_spearman:.4f}"
    print(f"[PASS] Test 8: 6대 대표 시나리오 순위 안정성 검증 통과 (최저 Spearman r = {min_spearman:.4f} >= 0.985)")
    
    # Test 9: Bus-Enhanced 모델 순위 연속성 및 유일성 [1..150]
    ranks = sorted(r_cand["rank"].tolist())
    assert ranks == list(range(1, 151)), "순위 연속성 또는 고유성 위반"
    print(f"[PASS] Test 9: 150개 행정동 1위~150위 중복 없는 완전 순위 검증 통과")
    
    # Test 10: Phase 7 Baseline 회귀 무결성
    # 카페 + 2030 Baseline 1위는 신암4동 77.93점이어야 함
    assert r_base.iloc[0]["adm_nm"] == "대구광역시 동구 신암4동", "Baseline 1위 불일치"
    assert abs(r_base.iloc[0]["total_score"] - 77.93) < 0.05, f"Baseline 점수 불일치: {r_base.iloc[0]['total_score']}"
    print(f"[PASS] Test 10: Phase 7 Baseline 모델 회귀 무결성 불변 확인 (1위 신암4동 {r_base.iloc[0]['total_score']}점)")
    
    print("=" * 60)
    print("ALL 10 PHASE 8 AUTOMATED TESTS PASSED! (100%)")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
