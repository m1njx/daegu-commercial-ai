#!/usr/bin/env python3
"""Generate and audit 3 models x 6 official demos x Top 5 explanations."""

from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.recommendation.explain import generate_explanation
from src.recommendation.feature_builder import build_dong_industry_features
from src.recommendation.improved import calculate_improved_scores, generate_improved_explanation
from src.recommendation.personalization import WEIGHT_PRESETS
from src.recommendation.ranking import rank_locations
from src.recommendation.scoring import calculate_component_scores, compute_total_score
from src.recommendation.transit_enhanced import calculate_enhanced_scores, generate_enhanced_explanation

DEMOS = (
    ("카페", "2030", "기본 균형형"),
    ("한식", "전체", "배후 수요 집중형 (대형 매장/안정형)"),
    ("미용실", "2030", "기본 균형형"),
    ("학원", "10대 이하", "타깃 고객 집중형 (트렌디/특화 소비)"),
    ("종합소매", "전체", "기본 균형형"),
    ("숙박", "2030", "기본 균형형"),
)
BAD = ("검증된 상권", "미검증 소규모 상권", "동종 업종 시너지", "집적 효과가 형성", "미포화 성장 기회", "성공 가능성")


def main() -> None:
    dong = pd.read_parquet(ROOT / "data/processed/feature_mart/commercial_feature_mart_dong.parquet")
    stores = pd.read_parquet(ROOT / "data/processed/feature_mart/store_spatial_features.parquet")
    bus = pd.read_parquet(ROOT / "data/processed/transit/bus/daegu_bus_dong_features.parquet")
    audited = 0
    for industry, target, preset in DEMOS:
        features, meta = build_dong_industry_features(industry, target, dong, stores)
        integrated_input = features.merge(bus.drop(columns=["adm_nm", "area_km2"]), on="adm_cd2", how="left")
        weights = WEIGHT_PRESETS[preset]
        model_frames = (
            ("baseline", compute_total_score(calculate_component_scores(features.copy()), weights), generate_explanation),
            ("improved", calculate_improved_scores(features.copy(), weights=weights), generate_improved_explanation),
            ("integrated", calculate_enhanced_scores(integrated_input, candidate="candidate_b", weights=weights), generate_enhanced_explanation),
        )
        for model, scored, generator in model_frames:
            top5 = rank_locations(scored, top_n=5)
            assert len(top5) == 5 and top5["total_score"].notna().all()
            for _, row in top5.iterrows():
                result = generator(row, meta)
                text = " ".join(result.get("strengths", []) + result.get("cautions", []))
                assert text.strip(), (model, industry, row["adm_nm"])
                assert not any(term in text for term in BAD), (model, industry, row["adm_nm"], text)
                if float(row.get("location_quotient", 0) or 0) < 1:
                    assert "대구 평균 대비 해당 업종 비중이 상대적으로 높" not in text
                if int(row.get("cat_store_count", 0) or 0) == 0:
                    assert "업종 집적도가 높은" not in text
                audited += 1
    assert audited == 90
    print("PHASE 22 EXPLANATIONS: 90/90 PASS")
    print("Numeric/runtime generation: PASS; stale claims: 0; LQ<1 overclaim: 0; zero-store contradiction: 0")


if __name__ == "__main__":
    main()
