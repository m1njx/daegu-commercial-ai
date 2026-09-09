# -*- coding: utf-8 -*-
"""
scripts/run_phase9_tests.py

Phase 9: Phase 8 Candidate B 정식 서비스 통합 10대 자동화 테스트 스위트
1. App import 및 구문 컴파일 무결성 검증 (py_compile)
2. 버스 데이터 로딩 및 피처 결합 무결성 검증 (150개 동 전수 결합, 결측치 0)
3. Candidate B (대중교통 통합 모델) 실행 및 유효성 검증 (점수 0~100)
4. 순위 연속성 및 유일성 검증 (1위~150위 완전 순위)
5. 6대 컴포넌트 전체 가중치 불변성 검증 (합계 1.0, 대중교통 15% 유지)
6. Phase 6 0점포 보정(alpha=0.50) 유지 검증
7. Baseline 및 Candidate B 이중 모델 접근성 검증
8. Phase 7 Baseline 회귀 무결성 검증 (신암4동 77.93 등 4대 기준값 불변)
9. 6대 데모 시나리오 Candidate B 정상 실행 및 1위 입지 검증
10. 대중교통 Data-Grounded 설명 생성기 무결성 및 금지어(유동인구/방문객 등) 완전 배제 검증
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
from src.recommendation.scoring import BASELINE_WEIGHTS
from src.recommendation.ranking import rank_locations
from src.recommendation.improved import calculate_improved_scores
from src.recommendation.transit_enhanced import (
    calculate_enhanced_scores,
    generate_enhanced_explanation,
    TRANSIT_CANDIDATES,
)
from src.recommendation.personalization import validate_and_normalize_weights

def run_phase9_tests():
    print("=" * 70)
    print("PHASE 9: Candidate B 정식 서비스 통합 10대 자동화 테스트 스위트")
    print("=" * 70)
    
    app_path = ROOT_DIR / "app" / "app.py"
    dong_path = ROOT_DIR / "data" / "processed" / "feature_mart" / "commercial_feature_mart_dong.parquet"
    store_path = ROOT_DIR / "data" / "processed" / "feature_mart" / "store_spatial_features.parquet"
    bus_path = PROCESSED_BUS_DIR / "daegu_bus_dong_features.parquet"
    
    # Test 1: App import 및 바이트코드 구문 컴파일 무결성 검증
    py_compile.compile(str(app_path), doraise=True)
    with open(app_path, "r", encoding="utf-8") as f:
        app_code = f.read()
    assert "MODEL_MODE_INTEGRATED" in app_code, "MODEL_MODE_INTEGRATED 누락"
    assert "calculate_enhanced_scores" in app_code, "calculate_enhanced_scores 누락"
    assert "generate_enhanced_explanation" in app_code, "generate_enhanced_explanation 누락"
    print("[PASS] Test 1: app/app.py 바이트코드 컴파일 및 핵심 심볼 검증 통과")
    
    # Test 2: 버스 데이터 로딩 및 피처 결합 무결성 검증
    df_dong = pd.read_parquet(dong_path)
    df_store = pd.read_parquet(store_path)
    df_bus_dong = pd.read_parquet(bus_path)
    
    bus_cols = [
        "dong_bus_stop_count", "dong_daily_bus_boarding", "dong_daily_bus_alighting",
        "dong_daily_bus_total", "dong_bus_stop_density", "dong_bus_ridership_per_stop",
        "avg_dist_to_bus_m", "ratio_stores_in_bus_300m"
    ]
    for col in bus_cols:
        df_dong[col] = df_bus_dong[col].values
        
    assert len(df_dong) == 150, f"행정동 수가 150개가 아님: {len(df_dong)}"
    for col in bus_cols:
        assert df_dong[col].isna().sum() == 0, f"결측치 존재: {col}"
        assert not np.isinf(df_dong[col]).any(), f"무한대 존재: {col}"
    print("[PASS] Test 2: 150개 행정동 버스 피처 결합 무결성(결측치 0, Inf 0) 통과")
    
    # Test 3: Candidate B 실행 및 점수 유효 범위 검증
    feats, meta = build_dong_industry_features("카페", "2030", df_dong, df_store)
    for col in bus_cols:
        feats[col] = df_dong[col].values
        
    cand_b_scored = calculate_enhanced_scores(feats, candidate="candidate_b", is_improved=True)
    assert (cand_b_scored["total_score"] >= 0.0).all() and (cand_b_scored["total_score"] <= 100.0).all()
    assert (cand_b_scored["accessibility_score"] >= 0.0).all() and (cand_b_scored["accessibility_score"] <= 100.0).all()
    assert (cand_b_scored["bus_accessibility_score"] >= 0.0).all() and (cand_b_scored["bus_accessibility_score"] <= 100.0).all()
    assert (cand_b_scored["subway_accessibility_score"] >= 0.0).all() and (cand_b_scored["subway_accessibility_score"] <= 100.0).all()
    print("[PASS] Test 3: Candidate B 실행 및 대중교통 점수 전수 [0.0, 100.0] 범위 검증 통과")
    
    # Test 4: 순위 유일성 및 1~150 완전 연속성 검증
    cand_b_ranked = rank_locations(cand_b_scored)
    ranks = sorted(cand_b_ranked["rank"].tolist())
    assert ranks == list(range(1, 151)), "1~150위 고유 순위 연속성 위반"
    print("[PASS] Test 4: 150개 행정동 1위부터 150위까지 결측/중복 없는 완전 순위 검증 통과")
    
    # Test 5: 6대 컴포넌트 전체 가중치 보존 검증
    assert BASELINE_WEIGHTS["demand"] == 0.30, "Demand 가중치 변조"
    assert BASELINE_WEIGHTS["target_fit"] == 0.20, "Target Fit 가중치 변조"
    assert BASELINE_WEIGHTS["competition"] == 0.15, "Competition 가중치 변조"
    assert BASELINE_WEIGHTS["accessibility"] == 0.15, "Accessibility 가중치 변조"
    assert BASELINE_WEIGHTS["parking"] == 0.10, "Parking 가중치 변조"
    assert BASELINE_WEIGHTS["industry_fit"] == 0.10, "Industry Fit 가중치 변조"
    norm_w = validate_and_normalize_weights(BASELINE_WEIGHTS)
    assert abs(sum(norm_w.values()) - 1.0) < 1e-6, "가중치 합계 1.0 위반"
    print("[PASS] Test 5: 6대 컴포넌트 가중치(대중교통 15% 내부 구성만 개선, 합계 100%) 불변성 검증 통과")
    
    # Test 6: Phase 6 0점포 보정(alpha=0.50) 유지 검증
    f_accom, m_accom = build_dong_industry_features("숙박", "2030", df_dong, df_store)
    for col in bus_cols:
        f_accom[col] = df_dong[col].values
    scored_accom = calculate_enhanced_scores(f_accom, candidate="candidate_b", is_improved=True, discount_factor=0.50)
    unentered_dongs = scored_accom[scored_accom["cat_store_count"] == 0]
    assert len(unentered_dongs) == 23, f"숙박업 0점포 동 수 불일치: {len(unentered_dongs)}"
    for _, row in unentered_dongs.iterrows():
        expected_adj = round(row["raw_competition_score"] * 0.50, 2)
        assert abs(row["competition_score"] - expected_adj) < 0.05, "alpha=0.50 할인 계산 오류"
    print("[PASS] Test 6: 숙박 23개 0점포 행정동 alpha=0.50 할인 보정 유지 검증 통과")
    
    # Test 7: Baseline 및 Candidate B 이중 모델 접근성 검증
    base_scored = calculate_enhanced_scores(feats, candidate="baseline", is_improved=True)
    base_ranked = rank_locations(base_scored)
    assert "accessibility_score" in base_ranked.columns
    assert "accessibility_score" in cand_b_ranked.columns
    assert TRANSIT_CANDIDATES["baseline"]["subway_weight"] == 1.00
    assert TRANSIT_CANDIDATES["candidate_b"]["subway_weight"] == 0.70
    assert TRANSIT_CANDIDATES["candidate_b"]["bus_weight"] == 0.30
    print("[PASS] Test 7: Baseline(철도 100%) 및 Candidate B(철도 70% + 버스 30%) 이중 모드 동시 지원 검증 통과")
    
    # Test 8: Phase 7 Baseline 회귀 무결성 검증 (4대 핵심 기준값 불변)
    sanity_cases = [
        ("카페", "2030", "신암4동", 77.93),
        ("한식", "전체", "진천동", 71.54),
        ("학원", "10대", "범어1동", 80.16),
        ("숙박", "2030", "감삼동", 77.00),
    ]
    for ind, tgt, exp_dong, exp_sc in sanity_cases:
        f, _ = build_dong_industry_features(ind, tgt, df_dong, df_store)
        r = rank_locations(calculate_enhanced_scores(f, candidate="baseline", is_improved=True))
        top1 = r.iloc[0]
        assert exp_dong in top1["adm_nm"], f"[{ind}+{tgt}] 1위 동 불일치: {top1['adm_nm']} != {exp_dong}"
        assert abs(top1["total_score"] - exp_sc) < 0.05, f"[{ind}+{tgt}] 점수 불일치: {top1['total_score']} != {exp_sc}"
    print("[PASS] Test 8: Phase 7 Baseline 4대 핵심 기준값 100% 불변 보존 검증 통과")
    
    # Test 9: 6대 데모 시나리오 Candidate B 정상 실행 및 검증
    expected_cand_b = [
        ("카페", "2030", "신암4동", 77.75),
        ("한식", "전체", "상인1동", 71.29),
        ("미용실", "2030", "칠성동", 75.45),
        ("학원", "10대", "범어1동", 78.68),
        ("종합소매", "전체", "상인1동", 72.22),
        ("숙박", "2030", "감삼동", 75.82),
    ]
    for ind, tgt, exp_dong, exp_sc in expected_cand_b:
        f, _ = build_dong_industry_features(ind, tgt, df_dong, df_store)
        for col in bus_cols:
            f[col] = df_dong[col].values
        r = rank_locations(calculate_enhanced_scores(f, candidate="candidate_b", is_improved=True))
        top1 = r.iloc[0]
        assert exp_dong in top1["adm_nm"], f"[{ind}+{tgt}] Candidate B 1위 불일치: {top1['adm_nm']} != {exp_dong}"
        assert abs(top1["total_score"] - exp_sc) < 0.05, f"[{ind}+{tgt}] Candidate B 점수 불일치: {top1['total_score']} != {exp_sc}"
    print("[PASS] Test 9: 6대 데모 시나리오 Candidate B 적용 결과 (신암4/상인1/칠성/범어1/상인1/감삼) 검증 통과")
    
    # Test 10: Data-Grounded 설명 생성기 무결성 및 금지어 완전 배제 검증
    for _, row in cand_b_ranked.head(10).iterrows():
        exp = generate_enhanced_explanation(row, meta)
        full_text = exp["summary_sentence"] + " " + " ".join(exp["strengths"]) + " " + " ".join(exp["cautions"])
        forbidden_words = ["실제 유동인구", "방문객 수", "고객 수", "소비자 수"]
        for bad in forbidden_words:
            assert bad not in full_text, f"금지어 검출: {bad} in {full_text}"
        assert len(exp["strengths"]) > 0, "강점 설명 생성 누락"
    print("[PASS] Test 10: Data-Grounded 설명 생성기 무결성 및 금지어 4종 완전 배제 검증 통과")
    
    print("=" * 70)
    print("ALL 10 PHASE 9 AUTOMATED TESTS PASSED! (100%)")
    print("=" * 70)
    return True

if __name__ == "__main__":
    success = run_phase9_tests()
    if not success:
        sys.exit(1)
