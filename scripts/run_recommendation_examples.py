#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/run_recommendation_examples.py

Phase 5: 5대 핵심 업종 추천 시나리오 정밀 실행 및 설명성·민감도·어블레이션 산출 스크립트
1) 카페 (타깃: 2030 청년 소비층)
2) 음식점 (한식, 타깃: 전체 인구)
3) 미용실 (이용·미용, 타깃: 2030 청년)
4) 학원 (일반·기타 교육, 타깃: 10대 이하)
5) 소매업 (종합 소매, 타깃: 전체 인구)
"""

import os
import sys
import json
import pandas as pd
import numpy as np

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from src.recommendation import (
    build_dong_industry_features,
    calculate_component_scores,
    compute_total_score,
    rank_locations,
    generate_explanation,
    run_sensitivity_analysis,
    run_ablation_test,
    BASELINE_WEIGHTS
)

def run_examples():
    print("=" * 80)
    print(" [PHASE 5] 5대 핵심 업종 창업 입지 추천 정밀 분석 및 사유·민감도 평가 ")
    print("=" * 80)
    
    dong_path = os.path.join(base_dir, "data/processed/feature_mart/commercial_feature_mart_dong.parquet")
    store_path = os.path.join(base_dir, "data/processed/feature_mart/store_spatial_features.parquet")
    df_dong = pd.read_parquet(dong_path)
    df_store = pd.read_parquet(store_path)
    
    test_cases = [
        {"industry": "카페", "target_age": "2030", "desc": "2030 청년층 타깃 카페 창업"},
        {"industry": "한식", "target_age": "all", "desc": "전체 인구 대상 한식 음식점 창업"},
        {"industry": "미용실", "target_age": "2030", "desc": "2030 청년층 타깃 헤어/뷰티살롱 창업"},
        {"industry": "학원", "target_age": "10s", "desc": "10대 학령기 인구 타깃 보습/입시 학원 창업"},
        {"industry": "종합소매", "target_age": "all", "desc": "전체 주민 대상 생활밀착형 종합 소매점 창업"},
    ]
    
    all_case_results = []
    
    for tc in test_cases:
        ind = tc["industry"]
        tgt = tc["target_age"]
        desc = tc["desc"]
        
        print("\n" + "#" * 80)
        print(f" ▶ 시나리오: {desc} (업종: {ind}, 타깃: {tgt})")
        print("#" * 80)
        
        feat_df, meta = build_dong_industry_features(ind, tgt, df_dong, df_store)
        scored_df = calculate_component_scores(feat_df)
        total_df = compute_total_score(scored_df, BASELINE_WEIGHTS)
        top10 = rank_locations(total_df, top_n=10)
        
        # 1. Top 10 테이블 출력
        print("\n[Top 10 추천 행정동]")
        display_cols = [
            "rank", "adm_nm", "total_score", "demand_score", "target_fit_score",
            "competition_score", "accessibility_score", "parking_score", "industry_fit_score",
            "cat_store_count", "pop_total"
        ]
        print(top10[display_cols].to_string(index=False))
        
        # 2. 1위~3위 추천 상세 사유 (Explainability)
        print("\n[상위 1~3위 데이터 기반 추천 사유 (Explainability)]")
        for i in range(min(3, len(top10))):
            row = top10.iloc[i]
            exp = generate_explanation(row, meta)
            print(f"\n  ({i+1}위) {exp['short_nm']} - 총점 {exp['total_score']}점")
            print(f"      * 요약: {exp['summary_sentence']}")
            for s in exp['strengths']:
                print(f"      + 강점: {s}")
            for c in exp['cautions']:
                print(f"      - 주의: {c}")
                
        # 3. 민감도 분석 (Sensitivity Analysis)
        sens_res = run_sensitivity_analysis(scored_df, top_k=10)
        print("\n[가중치 민감도 분석 (Sensitivity Analysis)]")
        print("  시나리오별 Top 10 일치율 및 Spearman 순위 상관계수:")
        for sc_name, s_val in sens_res.items():
            print(f"    - {sc_name:<16}: Top10 일치 {s_val['top_k_overlap_count']}/10 ({s_val['top_k_overlap_pct']}%), "
                  f"Spearman rho={s_val['spearman_rho']:.4f}, 평균순위변동={s_val['mean_rank_shift']}위")
                  
        # 4. 어블레이션 테스트 (Ablation Test)
        abl_res = run_ablation_test(scored_df, top_k=10)
        print("\n[컴포넌트 제외 영향도 검증 (Ablation Test)]")
        for ab_name, a_val in abl_res.items():
            print(f"    - {ab_name:<24}: Top10 일치 {a_val['top_k_overlap_count']}/10 ({a_val['top_k_overlap_pct']}%), "
                  f"Spearman rho={a_val['spearman_rho']:.4f}, 평균순위변동={a_val['mean_rank_shift']}위")
                  
        all_case_results.append({
            "scenario": desc,
            "industry": ind,
            "target_age": tgt,
            "top10": top10[display_cols].to_dict(orient="records"),
            "sensitivity": sens_res,
            "ablation": abl_res,
        })
        
    # 결과 JSON 저장 (리포트 작성 시 정확한 수치 인용용)
    res_json_path = os.path.join(base_dir, "reports/phase5_example_results.json")
    with open(res_json_path, "w", encoding="utf-8") as f:
        json.dump(all_case_results, f, ensure_ascii=False, indent=2)
    print(f"\n[저장 완료] 5대 시나리오 결과 JSON: {res_json_path}")

if __name__ == "__main__":
    run_examples()
