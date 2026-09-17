#!/usr/bin/env python3
"""Regenerate the historical Phase 7 demo fixture from current model semantics."""

from pathlib import Path
import json, sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.recommendation.feature_builder import build_dong_industry_features
from src.recommendation.improved import calculate_improved_scores, generate_improved_explanation
from src.recommendation.ranking import rank_locations
from src.recommendation.scoring import calculate_component_scores, compute_total_score

SCENARIOS = [
    ("카페 + 2030 청년 소비층", "카페", "2030"),
    ("한식 음식점 + 전체 인구", "한식", "전체"),
    ("미용실 + 2030 청년 소비층", "미용실", "2030"),
    ("학원 + 10대 이하", "학원", "10대"),
    ("종합소매 + 전체 인구", "종합소매", "전체"),
    ("숙박업 + 2030 청년층", "숙박", "2030"),
]


def record(row, explanation=None):
    out = {k: (int(row[k]) if k in {"rank", "cat_store_count"} else float(row[k]) if k.endswith("_score") else row[k])
           for k in ("rank", "adm_nm", "total_score", "cat_store_count", "market_status", "demand_score",
                     "target_fit_score", "competition_score", "accessibility_score", "parking_score", "industry_fit_score")
           if k in row.index}
    if explanation:
        out.update({k: explanation[k] for k in ("strengths", "cautions", "summary_sentence")})
    return out


def main():
    dong = pd.read_parquet(ROOT / "data/processed/feature_mart/commercial_feature_mart_dong.parquet")
    stores = pd.read_parquet(ROOT / "data/processed/feature_mart/store_spatial_features.parquet")
    result = {}
    for name, industry, target in SCENARIOS:
        feat, meta = build_dong_industry_features(industry, target, dong, stores)
        improved = rank_locations(calculate_improved_scores(feat, discount_factor=0.50))
        baseline = rank_locations(compute_total_score(calculate_component_scores(feat)))
        result[name] = {
            "industry": industry, "target": target,
            "industry_label": meta["industry_label"], "target_label": meta["target_demographic_label"],
            "city_industry_total": meta["city_industry_total"],
            "top5_improved": [record(row, generate_improved_explanation(row, meta)) for _, row in improved.head(5).iterrows()],
            "top5_baseline": [record(row) for _, row in baseline.head(5).iterrows()],
            "zero_store_count": int((feat["cat_store_count"] == 0).sum()),
        }
    path = ROOT / "reports/phase7_demo_results.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(path)


if __name__ == "__main__": main()
