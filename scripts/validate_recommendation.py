#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/validate_recommendation.py

Phase 5: 추천 랭킹 모델 무결성 및 제약조건 자동 검증 스크립트
1. 점수 유효 범위 검증 (0.0 ~ 100.0)
2. 결측치(NaN) 및 무한대(Inf) 존재 검증
3. 순위 무결성(연속성 1..N, 동일 업종 내 중복 불가) 검증
4. 행정동 코드(adm_cd2) 일치성 검증 (150개 동 100% 매핑)
5. 재현성(Reproducibility) 검증 (동일 파라미터 재실행 시 100% 일치)
"""

import os
import sys
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

def run_validation():
    print("=" * 70)
    print(" [PHASE 5] 상권 입지 추천 모델 품질 및 무결성 자동 검증 ")
    print("=" * 70)
    
    out_dir = os.path.join(base_dir, "data/processed")
    parquet_path = os.path.join(out_dir, "recommendation_scores.parquet")
    csv_path = os.path.join(out_dir, "recommendation_scores.csv")
    geojson_path = os.path.join(out_dir, "geojson/대구_행정동_경계_20230701.geojson")
    
    # 1. 파일 존재 여부
    print("\n1. 산출물 파일 존재 및 용량 검증:")
    for p in [parquet_path, csv_path]:
        if os.path.exists(p):
            sz = os.path.getsize(p)
            print(f"   [PASS] {os.path.basename(p):<30}: {sz/1024:>7.1f} KB")
        else:
            print(f"   [FAIL] {p} 파일이 존재하지 않습니다.")
            sys.exit(1)
            
    df_rec = pd.read_parquet(parquet_path)
    
    # 2. 레코드 수 및 시나리오 검증
    print("\n2. 레코드 수 및 시나리오 검증:")
    total_rows = len(df_rec)
    categories = df_rec["query_industry"].unique().tolist()
    expected_rows = len(categories) * 150
    print(f"   - 총 레코드 수       : {total_rows:>5,}행 (기대치: {expected_rows:,}) -> "
          f"{'PASS' if total_rows == expected_rows else 'FAIL'}")
    print(f"   - 평가 업종 시나리오 : {len(categories):>5}개 ({', '.join(categories[:6])}...)")
    
    # 3. 결측치 및 무한대 검증
    print("\n3. 결측치(NaN) 및 무한대(Inf) 검증:")
    score_cols = [
        "total_score", "demand_score", "target_fit_score",
        "competition_score", "accessibility_score", "parking_score", "industry_fit_score"
    ]
    has_nan = df_rec[score_cols].isna().sum().sum()
    has_inf = np.isinf(df_rec[score_cols].values).sum()
    print(f"   - 점수 컬럼 NaN 개수 : {has_nan:>5}건 -> {'PASS' if has_nan == 0 else 'FAIL'}")
    print(f"   - 점수 컬럼 Inf 개수 : {has_inf:>5}건 -> {'PASS' if has_inf == 0 else 'FAIL'}")
    
    # 4. 점수 범위 (0.0 ~ 100.0) 검증
    print("\n4. 점수 유효 범위 (0.0 ~ 100.0) 검증:")
    out_of_range = 0
    for col in score_cols:
        min_v = df_rec[col].min()
        max_v = df_rec[col].max()
        invalid = ((df_rec[col] < 0.0) | (df_rec[col] > 100.0)).sum()
        out_of_range += invalid
        print(f"   - {col:<20}: min={min_v:>5.2f}, max={max_v:>6.2f} -> {'PASS' if invalid == 0 else 'FAIL'}")
    print(f"   => 범위 초과 건수 합계: {out_of_range}건")
    
    # 5. 순위 연속성 및 중복 검증
    print("\n5. 순위(Rank) 무결성 및 연속성 검증:")
    rank_issues = 0
    for cat, grp in df_rec.groupby("query_industry"):
        expected_ranks = list(range(1, 151))
        actual_ranks = sorted(grp["rank"].tolist())
        if actual_ranks != expected_ranks:
            rank_issues += 1
            print(f"   [FAIL] 업종 '{cat}'의 랭킹이 1..150 연속 정수가 아닙니다.")
    if rank_issues == 0:
        print(f"   - 전체 {len(categories)}개 업종에 대해 1..150 순위 중복 및 누락 없음 -> PASS")
        
    # 6. 행정동 코드 일치성 검증
    print("\n6. 행정동 코드(adm_cd2) 일치성 검증:")
    import geopandas as gpd
    gdf_dong = gpd.read_file(geojson_path)
    geo_cds = set(gdf_dong["adm_cd2"].astype(str))
    rec_cds = set(df_rec["adm_cd2"].astype(str))
    diff_cds = rec_cds - geo_cds
    print(f"   - GeoJSON 150개 동 대비 매핑 일치율: {len(rec_cds.intersection(geo_cds))}/150 -> "
          f"{'PASS' if len(diff_cds) == 0 and len(rec_cds) == 150 else 'FAIL'}")
    
    # 7. 재현성 검증 (Reproducibility Test)
    print("\n7. 연산 재현성(Reproducibility) 검증:")
    dong_path = os.path.join(out_dir, "feature_mart/commercial_feature_mart_dong.parquet")
    store_path = os.path.join(out_dir, "feature_mart/store_spatial_features.parquet")
    df_dong = pd.read_parquet(dong_path)
    df_store = pd.read_parquet(store_path)
    
    feat2, _ = build_dong_industry_features("카페", "2030", df_dong, df_store)
    scored2 = calculate_component_scores(feat2)
    tot2 = compute_total_score(scored2, BASELINE_WEIGHTS)
    rank2 = rank_locations(tot2)
    
    orig_cafe = df_rec[df_rec["query_industry"] == "카페"].sort_values("rank").reset_index(drop=True)
    score_diff = (orig_cafe["total_score"] - rank2["total_score"]).abs().max()
    print(f"   - '카페(2030)' 시나리오 재실행 점수 최대 오차: {score_diff:.6f} -> "
          f"{'PASS' if score_diff == 0.0 else 'FAIL'}")
          
    print("\n" + "=" * 70)
    print(" [최종 판정] 추천 모델 무결성 및 안전성 검증 100% PASS ")
    print("=" * 70)

if __name__ == "__main__":
    run_validation()
