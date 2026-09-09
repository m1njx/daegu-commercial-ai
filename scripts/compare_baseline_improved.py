# -*- coding: utf-8 -*-
"""
scripts/compare_baseline_improved.py

BASELINE vs IMPROVED 추천 모델 정량 비교 및 민감도 분석 스크립트
- 주요 5대 일상 업종 및 특화 업종(숙박 등) 대상 정량 비교
- Top 10 일치율(Overlap), Spearman 순위 상관계수(rho), Top 5 순위 변화 분석
- 0개 점포 지역 영향도(순위 하락 및 점수 변화) 실증 추적
- 임계값(min_stores, discount_factor) 민감도 분석
- 결과를 reports/phase6_baseline_vs_improved.json 에 저장
"""

import sys
import os
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

# 프로젝트 루트 경로 등록
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.recommendation.feature_builder import build_dong_industry_features
from src.recommendation.scoring import calculate_component_scores, compute_total_score, BASELINE_WEIGHTS
from src.recommendation.ranking import rank_locations
from src.recommendation.improved import calculate_improved_scores

def run_comparison():
    print("==================================================")
    print("PHASE 6: BASELINE vs IMPROVED 추천 모델 비교 시작")
    print("==================================================")
    
    dong_path = ROOT_DIR / "data/processed/feature_mart/commercial_feature_mart_dong.parquet"
    store_path = ROOT_DIR / "data/processed/feature_mart/store_spatial_features.parquet"
    
    if not dong_path.exists() or not store_path.exists():
        raise FileNotFoundError("Feature Mart 파일이 존재하지 않습니다.")
        
    df_dong = pd.read_parquet(dong_path)
    df_store = pd.read_parquet(store_path)
    
    scenarios = [
        {"industry": "카페", "target": "2030", "desc": "카페 + 2030 청년층"},
        {"industry": "한식", "target": "전체", "desc": "한식 + 전체 인구"},
        {"industry": "미용실", "target": "2030", "desc": "미용실 + 2030 청년층"},
        {"industry": "학원", "target": "10대", "desc": "학원 + 10대 청소년층"},
        {"industry": "종합소매", "target": "전체", "desc": "종합소매 + 전체 인구"},
        {"industry": "숙박", "target": "2030", "desc": "숙박 + 2030 청년층 (0점포 상권 표본)"},
    ]
    
    results = {
        "metadata": {
            "total_dongs": len(df_dong),
            "total_stores": len(df_store),
            "baseline_weights": BASELINE_WEIGHTS,
            "default_min_stores": 1,
            "default_discount_factor": 0.50,
        },
        "scenarios": {},
        "threshold_sensitivity": {},
    }
    
    for sc in scenarios:
        ind = sc["industry"]
        tgt = sc["target"]
        desc = sc["desc"]
        print(f"\n--- 시나리오 분석: {desc} ---")
        
        # 1. Feature 빌드
        feat, meta = build_dong_industry_features(ind, tgt, df_dong, df_store)
        zero_store_mask = feat["cat_store_count"] == 0
        zero_store_count = int(zero_store_mask.sum())
        
        # 2. Baseline 점수 및 랭킹
        base_feat = calculate_component_scores(feat.copy())
        base_scored = compute_total_score(base_feat)
        base_ranked = rank_locations(base_scored)
        
        # 3. Improved 점수 및 랭킹
        imp_scored = calculate_improved_scores(feat.copy(), min_stores=1, discount_factor=0.50)
        imp_ranked = rank_locations(imp_scored)
        
        # 4. 순위 및 점수 결합 분석
        comp_df = base_ranked[["adm_cd2", "adm_nm", "rank", "total_score", "competition_score", "cat_store_count"]].rename(
            columns={"rank": "rank_base", "total_score": "score_base", "competition_score": "comp_score_base"}
        ).merge(
            imp_ranked[["adm_cd2", "rank", "total_score", "competition_score", "market_status"]].rename(
                columns={"rank": "rank_imp", "total_score": "score_imp", "competition_score": "comp_score_imp"}
            ),
            on="adm_cd2"
        )
        
        comp_df["rank_change"] = comp_df["rank_base"] - comp_df["rank_imp"]  # 양수면 개선에서 순위 상승
        comp_df["score_change"] = (comp_df["score_imp"] - comp_df["score_base"]).round(2)
        
        # 5. 통계 지표 계산
        rho, pval = spearmanr(comp_df["rank_base"], comp_df["rank_imp"])
        
        top10_base = set(comp_df.sort_values("rank_base").head(10)["adm_cd2"])
        top10_imp = set(comp_df.sort_values("rank_imp").head(10)["adm_cd2"])
        top10_overlap = len(top10_base & top10_imp)
        jaccard = round(top10_overlap / len(top10_base | top10_imp), 4)
        
        max_abs_rank_change = int(comp_df["rank_change"].abs().max())
        mean_abs_rank_change = round(float(comp_df["rank_change"].abs().mean()), 2)
        
        # 0개 점포 동 추적
        zero_dong_details = []
        if zero_store_count > 0:
            zero_dongs = comp_df[comp_df["cat_store_count"] == 0].sort_values("rank_base")
            for _, r in zero_dongs.iterrows():
                zero_dong_details.append({
                    "adm_nm": r["adm_nm"],
                    "rank_base": int(r["rank_base"]),
                    "rank_imp": int(r["rank_imp"]),
                    "rank_drop": int(r["rank_imp"] - r["rank_base"]),
                    "score_base": float(r["score_base"]),
                    "score_imp": float(r["score_imp"]),
                    "comp_base": float(r["comp_score_base"]),
                    "comp_imp": float(r["comp_score_imp"]),
                })
                
        # Top 5 비교
        top5_base_list = comp_df.sort_values("rank_base").head(5)[[
            "rank_base", "adm_nm", "cat_store_count", "score_base", "comp_score_base"
        ]].to_dict("records")
        top5_imp_list = comp_df.sort_values("rank_imp").head(5)[[
            "rank_imp", "adm_nm", "cat_store_count", "score_imp", "comp_score_imp", "market_status"
        ]].to_dict("records")
        
        sc_result = {
            "industry": ind,
            "target": tgt,
            "zero_store_dongs_count": zero_store_count,
            "spearman_rho": round(float(rho), 4),
            "spearman_pval": float(pval),
            "top10_overlap_count": top10_overlap,
            "top10_jaccard_similarity": jaccard,
            "max_abs_rank_change": max_abs_rank_change,
            "mean_abs_rank_change": mean_abs_rank_change,
            "top5_baseline": top5_base_list,
            "top5_improved": top5_imp_list,
            "zero_store_sample_changes": zero_dong_details[:5],
        }
        results["scenarios"][desc] = sc_result
        
        print(f"  - 0개 점포 행정동 수: {zero_store_count}개")
        print(f"  - Spearman rho: {rho:.4f}")
        print(f"  - Top 10 일치수: {top10_overlap}/10 (Jaccard: {jaccard:.2f})")
        print(f"  - 최대 순위 변동폭: {max_abs_rank_change}, 평균 변동폭: {mean_abs_rank_change}")
        
    # 6. 임계값 민감도 분석 (숙박 업종 기준)
    print("\n--- 임계값 민감도 분석 (숙박 시나리오) ---")
    feat_lodg, _ = build_dong_industry_features("숙박", "2030", df_dong, df_store)
    base_lodg = rank_locations(compute_total_score(calculate_component_scores(feat_lodg.copy())))
    
    sens_results = []
    for ms in [0, 1, 2, 3, 5]:
        for dfactor in [0.0, 0.3, 0.5, 0.7, 1.0]:
            imp = rank_locations(calculate_improved_scores(feat_lodg.copy(), min_stores=ms, discount_factor=dfactor))
            rho_val, _ = spearmanr(base_lodg["rank"], imp["rank"])
            t10_b = set(base_lodg.head(10)["adm_cd2"])
            t10_i = set(imp.head(10)["adm_cd2"])
            overlap = len(t10_b & t10_i)
            # 0점포 동 중 baseline 3위였던 용산1동의 순위 추적
            yongsan_rank = int(imp[imp["adm_nm"] == "대구광역시 달서구 용산1동"]["rank"].iloc[0])
            sens_results.append({
                "min_stores": ms,
                "discount_factor": dfactor,
                "spearman_rho": round(float(rho_val), 4),
                "top10_overlap": overlap,
                "yongsan1dong_rank": yongsan_rank,
            })
    results["threshold_sensitivity"]["lodging_sensitivity"] = sens_results
    
    out_path = ROOT_DIR / "reports/phase6_baseline_vs_improved.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        
    print(f"\n성공적으로 비교 결과가 저장되었습니다: {out_path}")
    return results

if __name__ == "__main__":
    run_comparison()
