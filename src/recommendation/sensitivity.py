# -*- coding: utf-8 -*-
"""
src/recommendation/sensitivity.py

민감도 분석(Sensitivity Analysis) 및 어블레이션 테스트(Ablation Test) 모듈
- 가중치 변동 시나리오별 순위 안정성(Spearman 상관계수, Top 10 일치율) 측정
- 컴포넌트별 기여도 검증(Ablation Test)
"""

import pandas as pd
import numpy as np
from scipy.stats import spearmanr
from typing import Dict, Any, List
from .scoring import compute_total_score, BASELINE_WEIGHTS
from .ranking import rank_locations

SCENARIO_WEIGHTS: Dict[str, Dict[str, float]] = {
    "Baseline": BASELINE_WEIGHTS,
    "Demand_Centric": {
        "demand": 0.45, "target_fit": 0.20, "competition": 0.10,
        "accessibility": 0.10, "parking": 0.08, "industry_fit": 0.07
    },
    "Target_Centric": {
        "demand": 0.20, "target_fit": 0.40, "competition": 0.10,
        "accessibility": 0.15, "parking": 0.05, "industry_fit": 0.10
    },
    "Transit_Centric": {
        "demand": 0.20, "target_fit": 0.15, "competition": 0.10,
        "accessibility": 0.35, "parking": 0.10, "industry_fit": 0.10
    },
}

def run_sensitivity_analysis(df_scored: pd.DataFrame, top_k: int = 10) -> Dict[str, Any]:
    """
    다양한 가중치 시나리오를 적용하여 추천 순위 변동성 및 안정성을 평가합니다.
    """
    results = {}
    baseline_ranked = rank_locations(compute_total_score(df_scored.copy(), BASELINE_WEIGHTS))
    base_top_set = set(baseline_ranked.head(top_k)["adm_cd2"])
    
    for sc_name, weights in SCENARIO_WEIGHTS.items():
        if sc_name == "Baseline":
            continue
            
        sc_ranked = rank_locations(compute_total_score(df_scored.copy(), weights))
        sc_top_set = set(sc_ranked.head(top_k)["adm_cd2"])
        
        # 1. Top K 일치율 및 Jaccard Index
        intersection_cnt = len(base_top_set.intersection(sc_top_set))
        jaccard = intersection_cnt / len(base_top_set.union(sc_top_set))
        
        # 2. 전체 150개 동 Spearman 순위 상관계수
        # adm_cd2 기준으로 순위 정렬 결합
        merged_rank = baseline_ranked[["adm_cd2", "rank"]].rename(columns={"rank": "rank_base"}).merge(
            sc_ranked[["adm_cd2", "rank"]].rename(columns={"rank": "rank_sc"}),
            on="adm_cd2"
        )
        rho, pval = spearmanr(merged_rank["rank_base"], merged_rank["rank_sc"])
        
        # 3. 순위 변동량 (절대치 평균 및 최대치)
        rank_diff = (merged_rank["rank_base"] - merged_rank["rank_sc"]).abs()
        mean_shift = rank_diff.mean()
        max_shift = rank_diff.max()
        
        results[sc_name] = {
            "weights": weights,
            "top_k_overlap_count": int(intersection_cnt),
            "top_k_overlap_pct": round(intersection_cnt / top_k * 100.0, 1),
            "jaccard_similarity": round(jaccard, 3),
            "spearman_rho": round(rho, 4),
            "spearman_pvalue": float(pval),
            "mean_rank_shift": round(mean_shift, 2),
            "max_rank_shift": int(max_shift),
        }
        
    return results

def run_ablation_test(df_scored: pd.DataFrame, top_k: int = 10) -> Dict[str, Any]:
    """
    핵심 컴포넌트를 하나씩 제외(Ablation)했을 때의 순위 변동을 측정하여
    각 컴포넌트의 실질적 영향력을 검증합니다.
    """
    baseline_ranked = rank_locations(compute_total_score(df_scored.copy(), BASELINE_WEIGHTS))
    base_top_set = set(baseline_ranked.head(top_k)["adm_cd2"])
    
    ablation_targets = {
        "No_Transit (교통 제외)": "accessibility",
        "No_Parking (주차 제외)": "parking",
        "No_Competition (경쟁 제외)": "competition",
        "No_Target_Fit (타깃 제외)": "target_fit",
        "No_Demand (수요 제외)": "demand",
    }
    
    results = {}
    for ab_name, comp_to_remove in ablation_targets.items():
        # 해당 컴포넌트 가중치 0 설정 후 나머지 재정규화
        ablated_weights = BASELINE_WEIGHTS.copy()
        ablated_weights[comp_to_remove] = 0.0
        tot_w = sum(ablated_weights.values())
        norm_weights = {k: v / tot_w for k, v in ablated_weights.items()}
        
        ab_ranked = rank_locations(compute_total_score(df_scored.copy(), norm_weights))
        ab_top_set = set(ab_ranked.head(top_k)["adm_cd2"])
        
        intersection_cnt = len(base_top_set.intersection(ab_top_set))
        jaccard = intersection_cnt / len(base_top_set.union(ab_top_set))
        
        merged_rank = baseline_ranked[["adm_cd2", "rank"]].rename(columns={"rank": "rank_base"}).merge(
            ab_ranked[["adm_cd2", "rank"]].rename(columns={"rank": "rank_ab"}),
            on="adm_cd2"
        )
        rho, pval = spearmanr(merged_rank["rank_base"], merged_rank["rank_ab"])
        rank_diff = (merged_rank["rank_base"] - merged_rank["rank_ab"]).abs()
        
        results[ab_name] = {
            "removed_component": comp_to_remove,
            "top_k_overlap_count": int(intersection_cnt),
            "top_k_overlap_pct": round(intersection_cnt / top_k * 100.0, 1),
            "jaccard_similarity": round(jaccard, 3),
            "spearman_rho": round(rho, 4),
            "mean_rank_shift": round(rank_diff.mean(), 2),
            "max_rank_shift": int(rank_diff.max()),
        }
        
    return results
