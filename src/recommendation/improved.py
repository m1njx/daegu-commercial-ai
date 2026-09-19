# -*- coding: utf-8 -*-
"""
src/recommendation/improved.py

개선(IMPROVED) 추천 모델 및 0개 점포 미진입 상권 보정 모듈
- Phase 5 Baseline 모델을 보존하면서, 0개 점포 지역의 왜곡(무경쟁 착시 현상)을 보정
- 해당 업종 점포 확인 지역과 점포 미확인 지역을 중립적으로 구분
- 시장 형성 리스크 할인 계수(Market Readiness Discount) 및 임계값 민감도 지원
- 설명 가능성(Explainability)에 점포 확인 상태 및 현장 확인 필요사항 명시
"""

from typing import Dict, Any, Optional, Tuple, List
import pandas as pd
import numpy as np

from src.recommendation.scoring import (
    to_percentile,
    BASELINE_WEIGHTS,
    validate_store_thresholds,
    validate_discount_factor,
)
from src.recommendation.personalization import validate_and_normalize_weights
from src.recommendation.ranking import rank_locations
from src.recommendation.explain import build_canonical_explanation

# 기본 개선 파라미터 (단일 정답이 아닌 기준 설정값)
DEFAULT_MIN_STORES: int = 1
DEFAULT_MIN_TOTAL_STORES: int = 0
DEFAULT_DISCOUNT_FACTOR: float = 0.50

def calculate_improved_scores(
    df_feat: pd.DataFrame,
    weights: Optional[Dict[str, float]] = None,
    min_stores: int = DEFAULT_MIN_STORES,
    min_total_stores: int = DEFAULT_MIN_TOTAL_STORES,
    discount_factor: float = DEFAULT_DISCOUNT_FACTOR,
    filter_unentered: bool = False,
) -> pd.DataFrame:
    """
    피처 데이터프레임으로부터 개선된 6대 컴포넌트 점수 및 총점을 산출합니다.
    
    개선 핵심 로직:
    1. 6대 컴포넌트 점수를 산출하되, 점포수 0개 지역의 경쟁 점수 착시를 보정합니다.
    2. 업종 점포수 < min_stores 이거나 동내 총점포수 < min_total_stores 인 행정동을
       '미진입/시장 미형성' 상권으로 분류합니다.
    3. 미진입 상권의 경우, 경쟁 기회 점수에 시장 미형성 리스크 할인 계수(discount_factor)를 적용합니다.
    4. filter_unentered=True인 경우, 미진입 상권을 최종 추천 랭킹에서 제외합니다.
    """
    min_stores, min_total_stores = validate_store_thresholds(min_stores, min_total_stores)
    discount_factor = validate_discount_factor(discount_factor)

    df = df_feat.copy()
    
    # 1. Base Component Scoring
    # (1) Demand Score
    p_pop = to_percentile(df["pop_total"])
    p_pop_dense = to_percentile(df["pop_density"])
    p_transit = to_percentile(df["dong_daily_ridership"])
    p_stores = to_percentile(df["total_stores"])
    
    demand_score = (
        0.35 * p_pop +
        0.25 * p_pop_dense +
        0.20 * p_transit +
        0.20 * p_stores
    ).round(2)
    
    # (2) Target Fit Score
    p_tgt_ratio = to_percentile(df["target_ratio"])
    p_tgt_pop = to_percentile(df["target_pop"])
    
    target_fit_score = (
        0.60 * p_tgt_ratio +
        0.40 * p_tgt_pop
    ).round(2)
    
    # (3) Competition Score (Raw Baseline)
    p_cap_opp = to_percentile(df["target_pop_per_store"])
    p_comp_penalty = to_percentile(df["cat_avg_comp_300m"], ascending=False)
    
    raw_comp_score = (
        0.50 * p_cap_opp +
        0.50 * p_comp_penalty
    ).round(2)
    
    # (4) Accessibility Score
    p_sub_dist = to_percentile(df["cat_avg_subway_dist"], ascending=False)
    p_sub_zone = to_percentile(df["cat_ratio_subway"])
    p_sub_flow = to_percentile(df["dong_daily_ridership"])
    
    accessibility_score = (
        0.50 * p_sub_dist +
        0.30 * p_sub_zone +
        0.20 * p_sub_flow
    ).round(2)
    
    # (5) Parking Score
    p_park_300m = to_percentile(df["cat_avg_parking_300m"])
    p_park_per_store = to_percentile(df["parking_capacity_per_store"])
    p_park_total = to_percentile(df["dong_total_parking_capacity"])
    
    parking_score = (
        0.50 * p_park_300m +
        0.30 * p_park_per_store +
        0.20 * p_park_total
    ).round(2)
    
    # (6) Industry Fit Score: LQ percentile only (no duplicate share signal)
    p_lq = to_percentile(df["location_quotient"])
    industry_fit_score = p_lq.round(2)
    
    # 2. 상권 형성 상태 분류 및 0개 점포 보정
    is_store_unentered = df["cat_store_count"] < min_stores
    is_scale_insufficient = df["total_stores"] < min_total_stores
    is_unentered = is_store_unentered | is_scale_insufficient
    
    market_status = np.where(
        ~is_unentered,
        "해당 업종 점포 확인 지역",
        np.where(df["cat_store_count"] == 0, "해당 업종 점포 미확인 지역", "해당 업종 점포가 적은 지역")
    )
    
    # 경쟁 기회 점수 할인 (시장 미형성 리스크 반영)
    adjusted_comp_score = np.where(
        is_unentered,
        (raw_comp_score * discount_factor).round(2),
        raw_comp_score
    )
    
    # 3. 데이터프레임에 점수 결합
    df["demand_score"] = demand_score.clip(0.0, 100.0)
    df["target_fit_score"] = target_fit_score.clip(0.0, 100.0)
    df["target_ratio_pct"] = p_tgt_ratio
    df["target_pop_pct"] = p_tgt_pop
    df["competition_score"] = adjusted_comp_score.clip(0.0, 100.0)
    df["raw_competition_score"] = raw_comp_score.clip(0.0, 100.0)
    df["accessibility_score"] = accessibility_score.clip(0.0, 100.0)
    df["parking_score"] = parking_score.clip(0.0, 100.0)
    df["industry_fit_score"] = industry_fit_score.clip(0.0, 100.0)
    
    df["market_status"] = market_status
    df["is_unentered"] = is_unentered
    
    # 4. 가중 총점 계산
    w = validate_and_normalize_weights(weights)
    total = (
        w["demand"] * df["demand_score"] +
        w["target_fit"] * df["target_fit_score"] +
        w["competition"] * df["competition_score"] +
        w["accessibility"] * df["accessibility_score"] +
        w["parking"] * df["parking_score"] +
        w["industry_fit"] * df["industry_fit_score"]
    ).round(2)
    
    df["total_score"] = total.clip(0.0, 100.0)
    
    if filter_unentered:
        df = df[~df["is_unentered"]].copy()
        
    return df

def generate_improved_explanation(row: pd.Series, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    개선 모델용 설명(Explainability) 생성 함수.
    (Canonical engine 호출)
    """
    return build_canonical_explanation(row, metadata, model_type="improved")
