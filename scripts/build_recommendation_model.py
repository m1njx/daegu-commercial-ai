#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/build_recommendation_model.py

Phase 5: 대구 상권 추천 모델 전체 데이터셋 빌드 스크립트
- 150개 행정동 전수 대상
- 10대 업종대분류 + 5대 핵심 일상업종(카페, 한식, 미용실, 학원, 종합소매) 일괄 추천 스코어링
- baseline 가중치 적용 및 컴포넌트 점수 산출
- 결과 저장:
  - data/processed/recommendation_scores.parquet
  - data/processed/recommendation_scores.csv
"""

import os
import sys
import time
import pandas as pd
import numpy as np

# 프로젝트 루트 경로 추가
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from src.recommendation import (
    build_dong_industry_features,
    calculate_component_scores,
    compute_total_score,
    rank_locations,
    BASELINE_WEIGHTS
)

def log(msg: str):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

def main():
    t0 = time.time()
    log("=== [PHASE 5] 대구 상권 창업 입지 추천 모델 전체 빌드 시작 ===")
    
    # 1. 원천 가공 데이터 로드
    mart_dir = os.path.join(base_dir, "data/processed/feature_mart")
    dong_path = os.path.join(mart_dir, "commercial_feature_mart_dong.parquet")
    store_path = os.path.join(mart_dir, "store_spatial_features.parquet")
    
    if not os.path.exists(dong_path) or not os.path.exists(store_path):
        log(f"[ERROR] 필수 데이터셋이 존재하지 않습니다: {dong_path} 또는 {store_path}")
        sys.exit(1)
        
    df_dong = pd.read_parquet(dong_path)
    df_store = pd.read_parquet(store_path)
    log(f"-> 행정동 마트: {len(df_dong)}개 행정동, 점포 공간피처: {len(df_store):,}개 점포 로드 완료")
    
    # 2. 추천 대상 업종 및 타깃 페르소나 설정
    # 10대 대분류 + 5대 대표 세부업종
    target_tasks = [
        # 5대 핵심 일상업종 (사용자 지정 필수 검증)
        {"industry": "카페", "target_age": "2030", "category_type": "중분류 (비알코올)"},
        {"industry": "한식", "target_age": "all", "category_type": "중분류 (한식 음식점)"},
        {"industry": "미용실", "target_age": "2030", "category_type": "중분류 (이용·미용)"},
        {"industry": "학원", "target_age": "10s", "category_type": "중분류 (일반·기타 교육)"},
        {"industry": "종합소매", "target_age": "all", "category_type": "중분류 (종합 소매)"},
        # 10대 대분류
        {"industry": "음식", "target_age": "all", "category_type": "대분류"},
        {"industry": "소매", "target_age": "all", "category_type": "대분류"},
        {"industry": "수리·개인", "target_age": "all", "category_type": "대분류"},
        {"industry": "과학·기술", "target_age": "30s", "category_type": "대분류"},
        {"industry": "교육", "target_age": "10s", "category_type": "대분류"},
        {"industry": "예술·스포츠", "target_age": "2030", "category_type": "대분류"},
        {"industry": "시설관리·임대", "target_age": "4050", "category_type": "대분류"},
        {"industry": "부동산", "target_age": "4050", "category_type": "대분류"},
        {"industry": "보건의료", "target_age": "60plus", "category_type": "대분류"},
        {"industry": "숙박", "target_age": "all", "category_type": "대분류"},
    ]
    
    all_recommendations = []
    
    for task in target_tasks:
        ind_q = task["industry"]
        tgt_q = task["target_age"]
        cat_t = task["category_type"]
        
        # 피처 빌드 -> 스코어링 -> 랭킹
        feat_df, meta = build_dong_industry_features(ind_q, tgt_q, df_dong, df_store)
        scored_df = calculate_component_scores(feat_df)
        total_df = compute_total_score(scored_df, BASELINE_WEIGHTS)
        ranked_df = rank_locations(total_df)
        
        ranked_df["query_industry"] = ind_q
        ranked_df["query_target_age"] = tgt_q
        ranked_df["industry_label"] = meta["industry_label"]
        ranked_df["target_demographic_label"] = meta["target_demographic_label"]
        ranked_df["category_type"] = cat_t
        
        all_recommendations.append(ranked_df)
        log(f"   [{ind_q}] (타깃: {tgt_q}) 추천 랭킹 산출 완료 -> 1위: {ranked_df.iloc[0]['adm_nm']} ({ranked_df.iloc[0]['total_score']}점)")
        
    df_all_rec = pd.concat(all_recommendations, ignore_index=True)
    log(f"-> 총 {len(target_tasks)}개 업종 시나리오 × 150개 동 = {len(df_all_rec):,}개 추천 평가 레코드 생성")
    
    # 3. 저장
    out_dir = os.path.join(base_dir, "data/processed")
    parquet_out = os.path.join(out_dir, "recommendation_scores.parquet")
    csv_out = os.path.join(out_dir, "recommendation_scores.csv")
    
    df_all_rec.to_parquet(parquet_out, index=False)
    df_all_rec.to_csv(csv_out, index=False, encoding="utf-8-sig")
    
    log(f"[저장 완료] Parquet: {parquet_out} ({os.path.getsize(parquet_out)/1024:.1f} KB)")
    log(f"[저장 완료] CSV    : {csv_out} ({os.path.getsize(csv_out)/1024:.1f} KB)")
    log(f"=== [PHASE 5 완료] 전체 소요시간: {time.time() - t0:.2f}초 ===")

if __name__ == "__main__":
    main()
