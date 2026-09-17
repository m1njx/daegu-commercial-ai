# -*- coding: utf-8 -*-
"""
scripts/run_phase6_tests.py

Phase 6 추천 Prototype 및 모델 자동화 검증 테스트 스위트
- 필수 10대 테스트 전수 자동화
  1. 카페 + 2030 (150개 동, 0~100점, NaN/Inf 0, 순위 1~150 유일성)
  2. 한식 + 전체 (150개 동, 0~100점, NaN/Inf 0, 순위 1~150 유일성)
  3. 미용실 + 2030 (150개 동, 0~100점, NaN/Inf 0, 순위 1~150 유일성)
  4. 학원 + 10대 (150개 동, 0~100점, NaN/Inf 0, 순위 1~150 유일성)
  5. 종합소매 + 전체 (150개 동, 0~100점, NaN/Inf 0, 순위 1~150 유일성)
  6. 사용자 가중치 극단값 테스트 (100% 단일 가중치, 전 가중치 0 등)
  7. 0점포 상권 보정 테스트 (숙박 23개 0점포 동 검증 및 감점 여부)
  8. 잘못된 입력값(Invalid Input) 예외 처리 테스트
  9. 가중치 합계 정규화(100%) 무결성 테스트
  10. UI 및 모듈 연동 무결성 테스트
"""

import sys
import os
from pathlib import Path
import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.recommendation.feature_builder import build_dong_industry_features
from src.recommendation.scoring import calculate_component_scores, compute_total_score, BASELINE_WEIGHTS
from src.recommendation.ranking import rank_locations
from src.recommendation.explain import generate_explanation
from src.recommendation.improved import calculate_improved_scores, generate_improved_explanation
from src.recommendation.personalization import (
    validate_and_normalize_weights,
    WEIGHT_PRESETS,
    is_baseline_weights,
    format_weights_summary
)

def run_all_tests():
    print("==================================================")
    print("PHASE 6: 10대 자동화 테스트 스위트 실행")
    print("==================================================")
    
    dong_path = ROOT_DIR / "data/processed/feature_mart/commercial_feature_mart_dong.parquet"
    store_path = ROOT_DIR / "data/processed/feature_mart/store_spatial_features.parquet"
    
    assert dong_path.exists(), f"파일 누락: {dong_path}"
    assert store_path.exists(), f"파일 누락: {store_path}"
    
    df_dong = pd.read_parquet(dong_path)
    df_store = pd.read_parquet(store_path)
    
    test_results = []
    
    # ----------------------------------------------------
    # Helper: 5대 핵심 업종 시나리오 검증 함수
    # ----------------------------------------------------
    def verify_scenario(test_num: int, ind: str, tgt: str, mode: str = "IMPROVED"):
        test_name = f"Test {test_num}: {ind} + {tgt} ({mode})"
        print(f"\n[실행] {test_name}")
        
        feat, meta = build_dong_industry_features(ind, tgt, df_dong, df_store)
        if mode == "BASELINE":
            scored = compute_total_score(calculate_component_scores(feat))
        else:
            scored = calculate_improved_scores(feat, min_stores=1, discount_factor=0.50)
            
        ranked = rank_locations(scored)
        
        # 1. 150개 행정동
        cnt = len(ranked)
        assert cnt == 150, f"행정동 수가 150개가 아님: {cnt}"
        
        # 2. 점수 0~100 범위
        min_sc = ranked["total_score"].min()
        max_sc = ranked["total_score"].max()
        assert 0.0 <= min_sc <= 100.0, f"최소 점수 범위 이탈: {min_sc}"
        assert 0.0 <= max_sc <= 100.0, f"최대 점수 범위 이탈: {max_sc}"
        
        # 3. NaN 및 Inf 없음
        nan_cnt = ranked["total_score"].isna().sum()
        inf_cnt = np.isinf(ranked["total_score"]).sum()
        assert nan_cnt == 0, f"NaN 발견: {nan_cnt}건"
        assert inf_cnt == 0, f"Inf 발견: {inf_cnt}건"
        
        # 4. 순위 1~150 연속성 및 중복 없음
        expected_ranks = list(range(1, 151))
        actual_ranks = list(ranked["rank"].values)
        assert actual_ranks == expected_ranks, "순위가 1부터 150까지 연속적이지 않거나 중복 존재"
        
        # 5. Explainability 정상 생성
        exp = generate_improved_explanation(ranked.iloc[0], meta) if mode == "IMPROVED" else generate_explanation(ranked.iloc[0], meta)
        assert len(exp["summary_sentence"]) > 0, "요약 문장 누락"
        assert exp["rank"] == 1, "1위 설명 순위 불일치"
        
        print(f"  -> PASS: 150개 행정동 전수 검증 (점수범위 {min_sc:.1f}~{max_sc:.1f}점, NaN/Inf 0건, 1위 {ranked.iloc[0]['adm_nm']})")
        test_results.append((test_name, "PASS"))

    # Test 1~5: 주요 5대 시나리오
    verify_scenario(1, "카페", "2030")
    verify_scenario(2, "한식", "전체")
    verify_scenario(3, "미용실", "2030")
    verify_scenario(4, "학원", "10대")
    verify_scenario(5, "종합소매", "전체")
    
    # Test 6: 사용자 가중치 극단값 테스트
    print("\n[실행] Test 6: 사용자 가중치 극단값(Extreme Weights) 검증")
    feat, _ = build_dong_industry_features("카페", "2030", df_dong, df_store)
    
    # 케이스 A: 배후수요 100%, 나머지 0%
    extreme_w1 = {"demand": 100.0, "target_fit": 0.0, "competition": 0.0, "accessibility": 0.0, "parking": 0.0, "industry_fit": 0.0}
    norm_w1 = validate_and_normalize_weights(extreme_w1)
    scored_ext1 = calculate_improved_scores(feat, weights=norm_w1)
    # 수요 100%이므로 total_score == demand_score 여야 함 (반올림 오차 +- 0.01 허용)
    diff1 = (scored_ext1["total_score"] - scored_ext1["demand_score"]).abs().max()
    assert diff1 <= 0.02, f"극단 가중치 일치 실패: diff={diff1}"
    
    # 케이스 B: 모든 가중치 0 (Fallback to baseline)
    all_zero_w = {k: 0.0 for k in BASELINE_WEIGHTS.keys()}
    norm_zero = validate_and_normalize_weights(all_zero_w)
    assert is_baseline_weights(norm_zero), "전부 0일 때 Baseline 복원 실패"
    
    # 케이스 C: 음수 가중치 입력 방어
    neg_w = {"demand": -50.0, "target_fit": 50.0, "competition": 50.0, "accessibility": 0.0, "parking": 0.0, "industry_fit": 0.0}
    norm_neg = validate_and_normalize_weights(neg_w)
    assert norm_neg["demand"] == 0.0, "음수 가중치 클리핑 실패"
    assert round(sum(norm_neg.values()), 4) == 1.0, "음수 입력 후 정규화 합계 1.0 미달"
    
    print("  -> PASS: 극단 가중치(100% Demand, 전 가중치 0, 음수 입력) 방어 및 정규화 정상 동작 확인")
    test_results.append(("Test 6: 사용자 가중치 극단값 검증", "PASS"))

    # Test 7: 업종 점포 0개 지역 테스트
    print("\n[실행] Test 7: 업종 점포 0개 지역 보정 및 검증 (숙박 업종)")
    feat_lodg, meta_lodg = build_dong_industry_features("숙박", "2030", df_dong, df_store)
    zero_cnt = (feat_lodg["cat_store_count"] == 0).sum()
    assert zero_cnt == 23, f"숙박 0개 점포 동 수 불일치: {zero_cnt}"
    
    # Baseline vs Improved 점수 비교
    base_l = rank_locations(compute_total_score(calculate_component_scores(feat_lodg.copy())))
    imp_l = rank_locations(calculate_improved_scores(feat_lodg.copy(), min_stores=1, discount_factor=0.50))
    
    # 달서구 용산1동(점포 0개)의 순위 추적
    yongsan_base = base_l[base_l["adm_nm"] == "대구광역시 달서구 용산1동"].iloc[0]
    yongsan_imp = imp_l[imp_l["adm_nm"] == "대구광역시 달서구 용산1동"].iloc[0]
    
    assert yongsan_base["rank"] == 3, f"Baseline 용산1동 순위 오류: {yongsan_base['rank']}"
    assert yongsan_imp["rank"] > 10, f"Improved 용산1동 보정 실패 (여전히 상위권): {yongsan_imp['rank']}"
    assert yongsan_imp["competition_score"] < yongsan_base["competition_score"], "경쟁 점수 미할인"
    
    # market_status 태깅 확인
    assert yongsan_imp["market_status"] == "해당 업종 점포 미확인 지역", f"상권 상태 라벨 오류: {yongsan_imp['market_status']}"
    
    print(f"  -> PASS: 0개 점포 23개 동 식별, 용산1동 3위 -> {yongsan_imp['rank']}위 정상 보정, 태깅 무결성 확인")
    test_results.append(("Test 7: 업종 점포 0개 지역 보정 검증", "PASS"))

    # Test 8: 잘못된 입력값 예외 처리 테스트
    print("\n[실행] Test 8: 잘못된 입력값(Invalid Input) 방어 검증")
    # 존재하지 않는 업종 검색
    invalid_ind_passed = False
    try:
        build_dong_industry_features("우주정거장운영업", "2030", df_dong, df_store)
    except ValueError:
        invalid_ind_passed = True
    assert invalid_ind_passed, "존재하지 않는 업종에 대해 ValueError가 발생하지 않음"
    
    # 알 수 없는 타깃 연령대 입력 시 Fallback 확인
    feat_fb, meta_fb = build_dong_industry_features("카페", "외계인연령층", df_dong, df_store)
    assert "2030" in meta_fb["target_demographic_label"], f"알 수 없는 연령 기본값 fallback 실패: {meta_fb}"
    
    print("  -> PASS: 비정상 업종 ValueError 차단 및 알 수 없는 연령 Fallback 정상 작동 확인")
    test_results.append(("Test 8: 잘못된 입력값 예외 방어 검증", "PASS"))

    # Test 9: 가중치 합계 정규화(100%) 무결성 테스트
    print("\n[실행] Test 9: 가중치 합계 100% 정규화 무결성 검증")
    test_cases = [
        {"demand": 30, "target_fit": 20, "competition": 15, "accessibility": 15, "parking": 10, "industry_fit": 10},
        {"demand": 50, "target_fit": 50, "competition": 50, "accessibility": 50, "parking": 50, "industry_fit": 50}, # 합계 300
        {"demand": 1, "target_fit": 2, "competition": 3, "accessibility": 4, "parking": 5, "industry_fit": 6},       # 합계 21
        {"demand": 0.1, "target_fit": 0.2, "competition": 0.3, "accessibility": 0.1, "parking": 0.1, "industry_fit": 0.2},
    ]
    for tc in test_cases:
        res = validate_and_normalize_weights(tc)
        tot = sum(res.values())
        assert abs(tot - 1.0) < 1e-3, f"가중치 정규화 합계 오류: {tot}"
        for v in res.values():
            assert v >= 0.0, "음수 가중치 발견"
            
    print("  -> PASS: 다양한 임의 가중치 입력에서 정규화 합계 100%(1.0) 무결성 확인")
    test_results.append(("Test 9: 가중치 정규화 무결성 검증", "PASS"))

    # Test 10: UI 및 모듈 연동 무결성 테스트
    print("\n[실행] Test 10: UI 및 모듈 연동 무결성 검증")
    # Streamlit 앱 파일 구문 및 import 검사
    app_path = ROOT_DIR / "app/app.py"
    assert app_path.exists(), f"app/app.py 파일 미존재: {app_path}"
    
    # app.py 구문 검증 완료 여부 확인
    import py_compile
    py_compile.compile(str(app_path), doraise=True)
    
    # 6개 프리셋 모두 유효한 가중치를 생성하는지 확인
    for p_name, p_w in WEIGHT_PRESETS.items():
        norm_p = validate_and_normalize_weights(p_w)
        assert abs(sum(norm_p.values()) - 1.0) < 1e-3, f"프리셋 '{p_name}' 정규화 오류"
        
    print("  -> PASS: app/app.py 구문 컴파일 및 6대 프리셋 가중치 무결성 확인")
    test_results.append(("Test 10: UI 및 모듈 연동 무결성 검증", "PASS"))

    # ----------------------------------------------------
    # 최종 결과 요약
    # ----------------------------------------------------
    print("\n==================================================")
    print("PHASE 6: 10대 자동화 테스트 종합 결과")
    print("==================================================")
    all_pass = True
    for name, status in test_results:
        print(f"  {name}: [{status}]")
        if status != "PASS":
            all_pass = False
            
    print(f"\n전체 테스트 결과: {'ALL 10 TESTS PASSED (100%)' if all_pass else 'TESTS FAILED'}")
    return all_pass

if __name__ == "__main__":
    success = run_all_tests()
    if not success:
        sys.exit(1)
