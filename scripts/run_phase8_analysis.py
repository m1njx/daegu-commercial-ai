# -*- coding: utf-8 -*-
"""
scripts/run_phase8_analysis.py

대구 시내버스 데이터 통합에 따른 접근성 고도화 및 6대 시나리오 비교 분석 스크립트
- Baseline(기존 Phase 7) vs Candidate A(80/20), B(70/30), C(60/40) 종합 시뮬레이션
- 비역세권 91개 행정동 vs 역세권 59개 행정동 편향 완화 효과 정량 분석
- 6개 대표 시나리오 순위 상관계수(Spearman), Top 5/10 Overlap, Jaccard 유사도 분석
- 순위 상승/하락 TOP 10 행정동의 원인 분석 및 이상치(터미널/차고지/군위군) 검증
- 무결성 검증 (NaN, Inf, 음수, 150개 고유 순위) 및 결과 JSON/MD 리포트 저장
"""

import sys
import os
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

# 프로젝트 루트 경로 등록
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.features.bus_features import build_bus_feature_mart, PROCESSED_BUS_DIR
from src.recommendation.feature_builder import build_dong_industry_features
from src.recommendation.scoring import (
    calculate_component_scores,
    compute_total_score,
    BASELINE_WEIGHTS,
)
from src.recommendation.ranking import rank_locations
from src.recommendation.improved import calculate_improved_scores
from src.recommendation.transit_enhanced import (
    calculate_enhanced_scores,
    TRANSIT_CANDIDATES,
)

DEMO_SCENARIOS = [
    {"id": "scenario_1", "name": "카페 창업", "industry": "카페", "target": "2030", "desc": "비알코올 음료점 + 2030 청년층"},
    {"id": "scenario_2", "name": "한식 음식점", "industry": "한식", "target": "전체", "desc": "한식 + 전체 인구"},
    {"id": "scenario_3", "name": "미용실 창업", "industry": "미용실", "target": "2030", "desc": "이용·미용 + 2030 청년층"},
    {"id": "scenario_4", "name": "학원 창업", "industry": "학원", "target": "10대", "desc": "일반·기타 교육 + 10대 학령기"},
    {"id": "scenario_5", "name": "종합 소매점", "industry": "종합소매", "target": "전체", "desc": "종합 소매 + 전체 인구"},
    {"id": "scenario_6", "name": "숙박업 창업", "industry": "숙박", "target": "2030", "desc": "숙박업 + 2030 청년층"},
]

def run_phase8_experiment():
    print("=" * 80)
    print(" [PHASE 8] 대구 시내버스 승하차 데이터 통합 및 대중교통 접근성 고도화 실험")
    print("=" * 80)
    
    # 1. 버스 Feature Mart 로드 또는 생성
    bus_feat_path = PROCESSED_BUS_DIR / "daegu_bus_dong_features.parquet"
    if not bus_feat_path.exists():
        print(">> 버스 Feature Mart 신규 생성 중...")
        _, df_bus_dong, bus_meta = build_bus_feature_mart(save=True)
    else:
        print(">> 기존 가공된 버스 Feature Mart 로드 완료.")
        df_bus_dong = pd.read_parquet(bus_feat_path)
        _, _, bus_meta = build_bus_feature_mart(save=False)
        
    # 2. 기본 데이터 로드
    dong_mart_path = ROOT_DIR / "data" / "processed" / "feature_mart" / "commercial_feature_mart_dong.parquet"
    store_mart_path = ROOT_DIR / "data" / "processed" / "feature_mart" / "store_spatial_features.parquet"
    
    df_dong = pd.read_parquet(dong_mart_path)
    df_store = pd.read_parquet(store_mart_path)
    
    # 버스 피처를 df_dong에 머지
    bus_cols = [
        "adm_cd2", "dong_bus_stop_count", "dong_daily_bus_boarding",
        "dong_daily_bus_alighting", "dong_daily_bus_total",
        "dong_bus_stop_density", "dong_bus_ridership_per_stop",
        "avg_dist_to_bus_m", "ratio_stores_in_bus_300m"
    ]
    df_dong_merged = df_dong.merge(df_bus_dong[bus_cols], on="adm_cd2", how="left")
    
    # 3. 지하철역 유/무 그룹 분류
    has_subway = df_dong_merged["dong_station_count"] > 0
    subway_dongs = df_dong_merged[has_subway]["adm_cd2"].tolist()
    no_subway_dongs = df_dong_merged[~has_subway]["adm_cd2"].tolist()
    
    print(f">> 대구 150개 행정동 중 도시철도역 보유: {len(subway_dongs)}개 (39.3%), 미보유: {len(no_subway_dongs)}개 (60.7%)")
    
    # 4. 6대 시나리오 시뮬레이션
    scenario_results = {}
    candidates = ["baseline", "candidate_a", "candidate_b", "candidate_c"]
    
    for sc in DEMO_SCENARIOS:
        sc_id = sc["id"]
        print(f"\n>> 시뮬레이션 실행: [{sc['name']}] ({sc['desc']})")
        
        # 동적 피처 빌드
        feats, _ = build_dong_industry_features(sc["industry"], sc["target"], df_dong_merged, df_store)
        # 버스 피처 포함 확인
        for col in bus_cols[1:]:
            feats[col] = df_dong_merged[col].values
            
        cand_dfs = {}
        for cand in candidates:
            if cand == "baseline":
                # Phase 7 기존 모델 (Improved alpha=0.50 + 100% Subway Accessibility)
                scored = calculate_improved_scores(feats)
                ranked = rank_locations(scored)
            else:
                # 버스 결합 후보 모델
                scored = calculate_enhanced_scores(feats, candidate=cand, is_improved=True)
                ranked = rank_locations(scored)
            cand_dfs[cand] = ranked
            
        base_ranked = cand_dfs["baseline"]
        
        sc_eval = {
            "name": sc["name"],
            "industry": sc["industry"],
            "target": sc["target"],
            "baseline_top10": base_ranked.head(10)[["rank", "adm_nm", "total_score", "accessibility_score"]].to_dict(orient="records"),
            "candidates": {}
        }
        
        for cand in ["candidate_a", "candidate_b", "candidate_c"]:
            cand_ranked = cand_dfs[cand]
            
            # Spearman Rank Correlation
            merged_ranks = base_ranked[["adm_cd2", "rank", "total_score", "accessibility_score"]].merge(
                cand_ranked[["adm_cd2", "rank", "total_score", "accessibility_score"]],
                on="adm_cd2",
                suffixes=("_base", "_cand")
            )
            spearman_corr, _ = spearmanr(merged_ranks["rank_base"], merged_ranks["rank_cand"])
            
            # Overlap & Jaccard
            top5_base = set(base_ranked.head(5)["adm_cd2"])
            top5_cand = set(cand_ranked.head(5)["adm_cd2"])
            top5_overlap = len(top5_base.intersection(top5_cand))
            
            top10_base = set(base_ranked.head(10)["adm_cd2"])
            top10_cand = set(cand_ranked.head(10)["adm_cd2"])
            top10_overlap = len(top10_base.intersection(top10_cand))
            jaccard_top10 = len(top10_base.intersection(top10_cand)) / len(top10_base.union(top10_cand))
            
            # Rank Shifts
            merged_ranks["rank_shift"] = merged_ranks["rank_base"] - merged_ranks["rank_cand"] # 양수: 순위 상승
            merged_ranks["abs_rank_shift"] = merged_ranks["rank_shift"].abs()
            
            max_pos_shift = merged_ranks.loc[merged_ranks["rank_shift"].idxmax()]
            max_neg_shift = merged_ranks.loc[merged_ranks["rank_shift"].idxmin()]
            
            avg_shift = merged_ranks["abs_rank_shift"].mean()
            
            # Non-subway vs Subway analysis
            merged_ranks["is_subway"] = merged_ranks["adm_cd2"].isin(subway_dongs)
            sub_stats = merged_ranks[merged_ranks["is_subway"]]
            no_sub_stats = merged_ranks[~merged_ranks["is_subway"]]
            
            sc_eval["candidates"][cand] = {
                "label": TRANSIT_CANDIDATES[cand]["label"],
                "spearman_correlation": round(float(spearman_corr), 4),
                "top5_overlap": int(top5_overlap),
                "top10_overlap": int(top10_overlap),
                "jaccard_similarity_top10": round(float(jaccard_top10), 4),
                "mean_abs_rank_shift": round(float(avg_shift), 2),
                "max_gainer": {
                    "adm_nm": df_dong_merged.loc[df_dong_merged["adm_cd2"] == max_pos_shift["adm_cd2"], "adm_nm"].values[0],
                    "base_rank": int(max_pos_shift["rank_base"]),
                    "cand_rank": int(max_pos_shift["rank_cand"]),
                    "shift": int(max_pos_shift["rank_shift"]),
                },
                "max_loser": {
                    "adm_nm": df_dong_merged.loc[df_dong_merged["adm_cd2"] == max_neg_shift["adm_cd2"], "adm_nm"].values[0],
                    "base_rank": int(max_neg_shift["rank_base"]),
                    "cand_rank": int(max_neg_shift["rank_cand"]),
                    "shift": int(max_neg_shift["rank_shift"]),
                },
                "subway_areas": {
                    "count": len(sub_stats),
                    "base_access_mean": round(float(sub_stats["accessibility_score_base"].mean()), 2),
                    "cand_access_mean": round(float(sub_stats["accessibility_score_cand"].mean()), 2),
                    "access_delta": round(float(sub_stats["accessibility_score_cand"].mean() - sub_stats["accessibility_score_base"].mean()), 2),
                    "mean_rank_shift": round(float(sub_stats["rank_shift"].mean()), 2),
                },
                "non_subway_areas": {
                    "count": len(no_sub_stats),
                    "base_access_mean": round(float(no_sub_stats["accessibility_score_base"].mean()), 2),
                    "cand_access_mean": round(float(no_sub_stats["accessibility_score_cand"].mean()), 2),
                    "access_delta": round(float(no_sub_stats["accessibility_score_cand"].mean() - no_sub_stats["accessibility_score_base"].mean()), 2),
                    "mean_rank_shift": round(float(no_sub_stats["rank_shift"].mean()), 2),
                },
                "top10": cand_ranked.head(10)[["rank", "adm_nm", "total_score", "accessibility_score"]].to_dict(orient="records"),
            }
            
        scenario_results[sc_id] = sc_eval
        
    # 5. 시나리오 1(카페+2030) 기준 Candidate B 상세 상승/하락 TOP 10 추출
    sc1_feats, _ = build_dong_industry_features("카페", "2030", df_dong_merged, df_store)
    for col in bus_cols[1:]:
        sc1_feats[col] = df_dong_merged[col].values
        
    sc1_base = rank_locations(calculate_improved_scores(sc1_feats))
    sc1_cand_b = rank_locations(calculate_enhanced_scores(sc1_feats, candidate="candidate_b", is_improved=True))
    
    sc1_compare = sc1_base[["adm_cd2", "adm_nm", "rank", "total_score", "accessibility_score"]].merge(
        sc1_cand_b[["adm_cd2", "rank", "total_score", "accessibility_score", "bus_accessibility_score", "subway_accessibility_score"]],
        on="adm_cd2",
        suffixes=("_base", "_b")
    ).merge(df_dong_merged[["adm_cd2", "dong_station_count", "dong_daily_bus_total", "dong_daily_ridership"]], on="adm_cd2")
    
    sc1_compare["rank_shift"] = sc1_compare["rank_base"] - sc1_compare["rank_b"]
    sc1_compare["score_delta"] = (sc1_compare["total_score_b"] - sc1_compare["total_score_base"]).round(2)
    sc1_compare["access_delta"] = (sc1_compare["accessibility_score_b"] - sc1_compare["accessibility_score_base"]).round(2)
    
    top_gainers = sc1_compare.sort_values("rank_shift", ascending=False).head(10)
    top_losers = sc1_compare.sort_values("rank_shift", ascending=True).head(10)
    
    # 6. 무결성 검사
    integrity_results = {
        "nan_count": int(sc1_cand_b.isnull().sum().sum()),
        "inf_count": int(np.isinf(sc1_cand_b.select_dtypes(include=np.number)).sum().sum()),
        "unique_ranks_count": int(sc1_cand_b["rank"].nunique()),
        "rank_min": int(sc1_cand_b["rank"].min()),
        "rank_max": int(sc1_cand_b["rank"].max()),
        "score_min": float(sc1_cand_b["total_score"].min()),
        "score_max": float(sc1_cand_b["total_score"].max()),
    }
    
    # 7. 종합 통계 저장 (JSON)
    output_data = {
        "metadata": bus_meta,
        "integrity": integrity_results,
        "scenarios": scenario_results,
        "candidate_b_top_gainers": top_gainers[[
            "adm_nm", "rank_base", "rank_b", "rank_shift", "score_delta",
            "access_delta", "dong_station_count", "dong_daily_bus_total", "dong_daily_ridership"
        ]].to_dict(orient="records"),
        "candidate_b_top_losers": top_losers[[
            "adm_nm", "rank_base", "rank_b", "rank_shift", "score_delta",
            "access_delta", "dong_station_count", "dong_daily_bus_total", "dong_daily_ridership"
        ]].to_dict(orient="records"),
    }
    
    json_out_path = ROOT_DIR / "reports" / "phase8_experiment_results.json"
    with open(json_out_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
        
    print(f"\n>> 실험 결과 저장 완료: {json_out_path}")
    print(">> 분석 요약:")
    for sc_id, sc_data in scenario_results.items():
        cb = sc_data["candidates"]["candidate_b"]
        print(f"  [{sc_data['name']}] Spearman: {cb['spearman_correlation']:.4f}, Top10 Overlap: {cb['top10_overlap']}/10, Jaccard: {cb['jaccard_similarity_top10']:.2f}, Mean Shift: {cb['mean_abs_rank_shift']:.1f} ranks")
        print(f"    비역세권 접근성 변화: {cb['non_subway_areas']['base_access_mean']} -> {cb['non_subway_areas']['cand_access_mean']} (Δ+{cb['non_subway_areas']['access_delta']})")
        print(f"    역세권 접근성 변화:   {cb['subway_areas']['base_access_mean']} -> {cb['subway_areas']['cand_access_mean']} (Δ{cb['subway_areas']['access_delta']})")

if __name__ == "__main__":
    run_phase8_experiment()
