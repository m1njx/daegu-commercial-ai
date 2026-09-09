# -*- coding: utf-8 -*-
"""
scripts/audit_30_explanations.py
6개 데모 시나리오 Candidate B 실행 및 Top 5 (총 30개) 설명 전수 데이터 근거성 감사
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.features.bus_features import PROCESSED_BUS_DIR
from src.recommendation.feature_builder import build_dong_industry_features
from src.recommendation.scoring import BASELINE_WEIGHTS
from src.recommendation.ranking import rank_locations
from src.recommendation.transit_enhanced import (
    calculate_enhanced_scores,
    generate_enhanced_explanation,
    TRANSIT_CANDIDATES,
)
from src.recommendation.personalization import WEIGHT_PRESETS

def audit():
    dong_path = ROOT_DIR / "data/processed/feature_mart/commercial_feature_mart_dong.parquet"
    store_path = ROOT_DIR / "data/processed/feature_mart/store_spatial_features.parquet"
    bus_path = PROCESSED_BUS_DIR / "daegu_bus_dong_features.parquet"

    df_dong = pd.read_parquet(dong_path)
    df_store = pd.read_parquet(store_path)
    df_bus = pd.read_parquet(bus_path)

    bus_cols = [
        "dong_bus_stop_count", "dong_daily_bus_boarding", "dong_daily_bus_alighting",
        "dong_daily_bus_total", "dong_bus_stop_density", "dong_bus_ridership_per_stop",
        "avg_dist_to_bus_m", "ratio_stores_in_bus_300m"
    ]
    for col in bus_cols:
        df_dong[col] = df_bus[col].values

    scenarios = [
        ("시나리오 1: 카페 + 2030", "카페", "2030", None),
        ("시나리오 2: 한식 + 전체", "한식", "전체", "배후 수요 집중형 (대형 매장/안정형)"),
        ("시나리오 3: 미용실 + 2030", "미용실", "2030", None),
        ("시나리오 4: 학원 + 10대", "학원", "10대", "타깃 고객 집중형 (트렌디/특화 소비)"),
        ("시나리오 5: 종합소매 + 전체", "종합소매", "전체", None),
        ("시나리오 6: 숙박 + 2030", "숙박", "2030", None),
    ]

    forbidden_terms = [
        "성공 확률", "창업 성공", "예상 매출", "예상 수익", "대출 승인", "실제 고객 수",
        "실제 방문객 수", "실제 소비자 수", "관광지", "핫플레이스", "유동인구", "10개 행정동 fallback",
        "노선 수", "대출 자동 추천", "대출 가능 금액"
    ]

    total_explanations = 0
    hallucination_count = 0
    discrepancy_count = 0

    print("=" * 80)
    print("6개 데모 시나리오 Candidate B 실행 및 30개 추천 설명 전수 감사")
    print("=" * 80)

    for title, ind, tgt, preset in scenarios:
        f, meta = build_dong_industry_features(ind, tgt, df_dong, df_store)
        for col in bus_cols:
            f[col] = df_dong[col].values
        w = WEIGHT_PRESETS[preset] if preset else BASELINE_WEIGHTS
        scored = calculate_enhanced_scores(f, candidate="candidate_b", weights=w, is_improved=True)
        ranked = rank_locations(scored)
        
        top5 = ranked.head(5)
        top1 = top5.iloc[0]
        adm = top1["adm_nm"]
        tot = top1["total_score"]
        acc = top1["accessibility_score"]
        sub = top1["subway_accessibility_score"]
        bus = top1["bus_accessibility_score"]
        print(f"\n[{title}]")
        print(f"  -> 1위: {adm} | 종합: {tot:.2f}점 | 접근성: {acc:.2f}점 (철도: {sub:.2f}, 버스: {bus:.2f})")
        print("  Top 5:", [f"{r['rank']}위 {r['adm_nm'].split()[-1]}({r['total_score']:.2f}점)" for _, r in top5.iterrows()])
        
        for rank_idx, (_, row) in enumerate(top5.iterrows(), 1):
            total_explanations += 1
            exp = generate_enhanced_explanation(row, meta)
            full_text = exp["summary_sentence"] + " " + " ".join(exp["strengths"]) + " " + " ".join(exp["cautions"])
            
            # Check forbidden
            for term in forbidden_terms:
                if term in full_text:
                    adm_name = row["adm_nm"]
                    print(f"  [HALLUCINATION] {adm_name} (Rank {rank_idx}): 금지어 '{term}' 발견!")
                    hallucination_count += 1
                    
            # Check bus stop count consistency
            stop_cnt = int(row["dong_bus_stop_count"])
            for s in exp["strengths"]:
                if "정류소" in s and f"{stop_cnt}개소" not in s:
                    print(f"  [DISCREPANCY] 정류소 수치 불일치: {s} vs {stop_cnt}개소")
                    discrepancy_count += 1

    print("\n" + "=" * 80)
    print(f"총 검증 설명 수: {total_explanations}개 (6개 데모 × Top 5)")
    print(f"Hallucination 검출 수: {hallucination_count}건")
    print(f"데이터 불일치 건수: {discrepancy_count}건")
    print("=" * 80)

if __name__ == "__main__":
    audit()
