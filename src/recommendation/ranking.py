# -*- coding: utf-8 -*-
"""
src/recommendation/ranking.py

추천 결과 정렬 및 랭킹 부여 모듈
- 동점자 처리 규칙(총점 -> 수요점수 -> 타깃적합도 순)
- 1부터 N까지의 연속 랭킹 부여 및 무결성 검증
"""

import pandas as pd
from typing import Optional

def rank_locations(df_scored: pd.DataFrame, top_n: Optional[int] = None) -> pd.DataFrame:
    """
    total_score를 기준으로 내림차순 정렬하여 1부터 순위를 부여합니다.
    """
    df = df_scored.copy()
    
    # 정렬 기준 (동점자 방지 다중 정렬)
    sort_cols = ["total_score", "demand_score", "target_fit_score", "pop_total"]
    df = df.sort_values(by=sort_cols, ascending=[False, False, False, False]).reset_index(drop=True)
    
    # 1부터 시작하는 순위 부여
    df["rank"] = df.index + 1
    
    # 출력 컬럼 정리
    primary_cols = [
        "rank", "adm_nm", "signgu_nm", "adm_cd2", "total_score",
        "demand_score", "target_fit_score", "competition_score",
        "accessibility_score", "parking_score", "industry_fit_score"
    ]
    detail_cols = [
        "cat_store_count", "pop_total", "target_pop", "target_ratio",
        "location_quotient", "dong_daily_ridership", "cat_avg_subway_dist",
        "cat_avg_comp_300m", "dong_total_parking_capacity", "parking_capacity_per_store"
    ]
    
    ordered_cols = primary_cols + [c for c in detail_cols if c in df.columns]
    remaining_cols = [c for c in df.columns if c not in ordered_cols]
    df = df[ordered_cols + remaining_cols]
    
    if top_n is not None:
        if top_n <= 0:
            raise ValueError("top_n은 None 또는 1 이상의 정수여야 합니다.")
        return df.head(top_n).copy()
    return df
