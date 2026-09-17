#!/usr/bin/env python3
"""Reproduce Phase 21 semantics and compare them with Phase 22 definitions."""

from pathlib import Path
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.recommendation.feature_builder import build_dong_industry_features, resolve_industry_filter
from src.recommendation.personalization import WEIGHT_PRESETS, validate_and_normalize_weights
from src.recommendation.ranking import rank_locations
from src.recommendation.scoring import to_percentile
from src.recommendation.transit_enhanced import calculate_enhanced_scores


SCENARIOS = [
    ("카페", "2030", "기본 균형형"),
    ("한식", "전체", "배후 수요 집중형 (대형 매장/안정형)"),
    ("미용실", "2030", "기본 균형형"),
    ("학원", "10대", "타깃 고객 집중형 (트렌디/특화 소비)"),
    ("종합소매", "전체", "기본 균형형"),
    ("숙박", "2030", "기본 균형형"),
]


def load_data():
    dong = pd.read_parquet(ROOT / "data/processed/feature_mart/commercial_feature_mart_dong.parquet")
    stores = pd.read_parquet(ROOT / "data/processed/feature_mart/store_spatial_features.parquet")
    bus = pd.read_parquet(ROOT / "data/processed/transit/bus/daegu_bus_dong_features.parquet")
    return dong, stores, bus


def add_bus(features, bus):
    return features.merge(bus.drop(columns=["adm_nm", "area_km2"]), on="adm_cd2", how="left")


def phase21_features(query, target, dong, stores, bus):
    features, metadata = build_dong_industry_features(query, target, dong, stores)
    clean = stores.copy()
    clean["indsMclsNm"] = clean["indsMclsNm"].astype(str).str.strip()
    clean["indsLclsNm"] = clean["indsLclsNm"].astype(str).str.strip()
    mask, _ = resolve_industry_filter(query, clean)
    legacy_comp = clean.loc[mask].groupby("adm_cd2")["competitor_mcls_count_300m"].mean()
    features["cat_avg_comp_300m"] = features["adm_cd2"].map(legacy_comp).fillna(0).round(1)
    return add_bus(features, bus), metadata


def phase21_scores(features, weights):
    scored = calculate_enhanced_scores(
        features, weights=weights, candidate="candidate_b", is_improved=True, discount_factor=0.50
    )
    old_fit = (
        0.60 * to_percentile(features["location_quotient"])
        + 0.40 * to_percentile(features["store_share_in_dong"])
    ).round(2)
    w = validate_and_normalize_weights(weights)
    scored["industry_fit_score"] = old_fit
    scored["total_score"] = (
        w["demand"] * scored["demand_score"]
        + w["target_fit"] * scored["target_fit_score"]
        + w["competition"] * scored["competition_score"]
        + w["accessibility"] * scored["accessibility_score"]
        + w["parking"] * scored["parking_score"]
        + w["industry_fit"] * scored["industry_fit_score"]
    ).round(2)
    return rank_locations(scored)


def summarize_delta(series):
    return {
        "min": float(series.min()), "max": float(series.max()),
        "mean": float(series.mean()), "median": float(series.median()),
        "p95_abs": float(series.abs().quantile(0.95)),
    }


def markdown_table(frame):
    values = frame.astype(str)
    header = "| " + " | ".join(values.columns) + " |"
    rule = "| " + " | ".join(["---"] * len(values.columns)) + " |"
    body = ["| " + " | ".join(row) + " |" for row in values.to_numpy().tolist()]
    return "\n".join([header, rule, *body])


def main():
    dong, stores, bus = load_data()
    rows = []
    all_deltas = []
    for query, target, preset in SCENARIOS:
        old_feat, _ = phase21_features(query, target, dong, stores, bus)
        new_feat, _ = build_dong_industry_features(query, target, dong, stores)
        new_feat = add_bus(new_feat, bus)
        old = phase21_scores(old_feat, WEIGHT_PRESETS[preset])
        new = rank_locations(calculate_enhanced_scores(
            new_feat, weights=WEIGHT_PRESETS[preset], candidate="candidate_b", discount_factor=0.50
        ))
        merged = old[["adm_cd2", "adm_nm", "rank", "total_score", "competition_score", "industry_fit_score"]].merge(
            new[["adm_cd2", "rank", "total_score", "competition_score", "industry_fit_score"]],
            on="adm_cd2", suffixes=("_before", "_after")
        )
        for field in ["rank", "total_score", "competition_score", "industry_fit_score"]:
            merged[f"{field}_delta"] = merged[f"{field}_after"] - merged[f"{field}_before"]
        merged["scenario"] = query
        all_deltas.append(merged)
        rho = float(spearmanr(merged["rank_before"], merged["rank_after"]).statistic)
        old5 = set(old.head(5)["adm_cd2"]); new5 = set(new.head(5)["adm_cd2"])
        rows.append({
            "업종": query,
            "변경 전 1위": old.iloc[0]["adm_nm"].split()[-1],
            "변경 전 점수": old.iloc[0]["total_score"],
            "변경 후 1위": new.iloc[0]["adm_nm"].split()[-1],
            "변경 후 점수": new.iloc[0]["total_score"],
            "Spearman": round(rho, 4),
            "Top5 일치": len(old5 & new5),
        })

    combined = pd.concat(all_deltas, ignore_index=True)
    score_stats = summarize_delta(combined["total_score_delta"])
    rank_stats = summarize_delta(combined["rank_delta"])
    top_rank = combined.reindex(combined["rank_delta"].abs().sort_values(ascending=False).index).head(10)
    top_score = combined.reindex(combined["total_score_delta"].abs().sort_values(ascending=False).index).head(10)

    # Independent reproduction of the reported Seongnae 1-dong restaurant scope mismatch.
    old_food, _ = phase21_features("음식점", "전체", dong, stores, bus)
    new_food, _ = build_dong_industry_features("음식점", "전체", dong, stores)
    old_row = old_food[old_food["adm_nm"].str.endswith("성내1동")].iloc[0]
    new_row = new_food[new_food["adm_nm"].str.endswith("성내1동")].iloc[0]

    out = ROOT / "reports/phase22_impact_analysis.md"
    lines = [
        "# Phase 22 Model Impact Analysis", "",
        "## Competition Scope Reproduction", "",
        f"- 성내1동 음식점 변경 전(점포별 중분류 평균): **{old_row['cat_avg_comp_300m']:.1f}개**",
        f"- 성내1동 음식점 변경 후(선택 음식업 전체): **{new_row['cat_avg_comp_300m']:.1f}개**", "",
        "## Six Official Demos", "", markdown_table(pd.DataFrame(rows)), "",
        "## 900 Rows Summary (150 Dongs x 6 Demos)", "",
        f"- Total score delta: {score_stats}",
        f"- Rank delta: {rank_stats}", "",
        "## Largest Absolute Rank Changes", "",
        markdown_table(top_rank[["scenario", "adm_nm", "rank_before", "rank_after", "rank_delta", "total_score_delta"]]), "",
        "## Largest Absolute Score Changes", "",
        markdown_table(top_score[["scenario", "adm_nm", "total_score_before", "total_score_after", "total_score_delta", "rank_delta"]]), "",
    ]
    out.write_text("\n".join(lines), encoding="utf-8")
    print(out)
    print(pd.DataFrame(rows).to_string(index=False))
    print("score_stats", score_stats)
    print("rank_stats", rank_stats)
    print(top_rank[["scenario", "adm_nm", "rank_before", "rank_after", "rank_delta", "total_score_delta"]].to_string(index=False))


if __name__ == "__main__":
    main()
