#!/usr/bin/env python3
"""Measure the impact of removing premature rounding from runtime LQ."""

import json
import sys
from pathlib import Path

import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.recommendation.feature_builder import build_dong_industry_features
from src.recommendation.personalization import WEIGHT_PRESETS
from src.recommendation.ranking import rank_locations
from src.recommendation.transit_enhanced import calculate_enhanced_scores

DONG = pd.read_parquet(ROOT / "data/processed/feature_mart/commercial_feature_mart_dong.parquet")
STORES = pd.read_parquet(ROOT / "data/processed/feature_mart/store_spatial_features.parquet")
BUS = pd.read_parquet(ROOT / "data/processed/transit/bus/daegu_bus_dong_features.parquet")

DEMOS = [
    ("카페", "2030", "기본 균형형"),
    ("한식", "전체", "배후 수요 집중형 (대형 매장/안정형)"),
    ("미용실", "2030", "기본 균형형"),
    ("학원", "10대", "타깃 고객 집중형 (트렌디/특화 소비)"),
    ("종합소매", "전체", "기본 균형형"),
    ("숙박", "2030", "기본 균형형"),
]


def ranked_pair(industry, target, preset):
    current, _ = build_dong_industry_features(industry, target, DONG, STORES)
    old = current.copy()
    city_share = current.cat_store_count.sum() / len(STORES)
    old["location_quotient"] = (old["store_share_in_dong"] / city_share).round(3)
    bus = BUS.drop(columns=["adm_nm", "area_km2"])
    old = old.merge(bus, on="adm_cd2", how="left")
    current = current.merge(bus, on="adm_cd2", how="left")
    weights = WEIGHT_PRESETS[preset]
    return (
        rank_locations(calculate_enhanced_scores(old, weights, "candidate_b", discount_factor=.5)),
        rank_locations(calculate_enhanced_scores(current, weights, "candidate_b", discount_factor=.5)),
    )


def main():
    output = {"cause": "runtime LQ premature 4-decimal share rounding removed", "scenarios": []}
    all_changes = []
    for industry, target, preset in DEMOS:
        before, after = ranked_pair(industry, target, preset)
        merged = before[["adm_cd2", "adm_nm", "rank", "total_score", "industry_fit_score", "location_quotient"]].merge(
            after[["adm_cd2", "rank", "total_score", "industry_fit_score", "location_quotient"]], on="adm_cd2", suffixes=("_before", "_after")
        )
        merged["score_delta"] = merged.total_score_after - merged.total_score_before
        merged["rank_delta"] = merged.rank_before - merged.rank_after
        merged["industry_fit_delta"] = merged.industry_fit_score_after - merged.industry_fit_score_before
        merged["scenario"] = f"{industry}+{target}"
        all_changes.append(merged)
        rho = float(spearmanr(merged.rank_before, merged.rank_after).statistic)
        overlap = len(set(before.head(5).adm_cd2) & set(after.head(5).adm_cd2))
        output["scenarios"].append({
            "scenario": f"{industry}+{target}", "preset": preset,
            "before_top1": before.iloc[0][["adm_nm", "total_score"]].to_dict(),
            "after_top1": after.iloc[0][["adm_nm", "total_score"]].to_dict(),
            "spearman": round(rho, 6), "top5_overlap": overlap,
            "max_abs_score_delta": round(float(merged.score_delta.abs().max()), 4),
            "max_abs_rank_delta": int(merged.rank_delta.abs().max()),
        })
    changes = pd.concat(all_changes, ignore_index=True)
    output["overall"] = {
        "rows": len(changes),
        "score_delta_min": round(float(changes.score_delta.min()), 4),
        "score_delta_max": round(float(changes.score_delta.max()), 4),
        "score_delta_mean": round(float(changes.score_delta.mean()), 6),
        "score_delta_median": round(float(changes.score_delta.median()), 6),
        "score_delta_p95_abs": round(float(changes.score_delta.abs().quantile(.95)), 4),
        "max_abs_rank_delta": int(changes.rank_delta.abs().max()),
    }
    output["top10_rank_changes"] = changes.assign(abs_rank=changes.rank_delta.abs()).sort_values(
        ["abs_rank", "scenario", "adm_cd2"], ascending=[False, True, True]
    ).head(10)[["scenario", "adm_nm", "rank_before", "rank_after", "rank_delta", "total_score_before", "total_score_after"]].to_dict("records")
    output["top10_score_changes"] = changes.assign(abs_score=changes.score_delta.abs()).sort_values(
        ["abs_score", "scenario", "adm_cd2"], ascending=[False, True, True]
    ).head(10)[["scenario", "adm_nm", "total_score_before", "total_score_after", "score_delta", "rank_before", "rank_after"]].to_dict("records")
    target = ROOT / "reports/phase24_impact_analysis.json"
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
