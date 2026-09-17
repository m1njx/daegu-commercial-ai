# -*- coding: utf-8 -*-
"""
src/recommendation/scoring.py

추천 컴포넌트 점수 및 가중 총합 점수(0~100) 계산 모듈
- 백분위수(Percentile Rank) 기반 비모수적 스케일링으로 이상치 왜곡 방지
- 6대 컴포넌트: Demand, Target Fit, Competition, Accessibility, Parking, Industry Fit
- 초기 Baseline 가중치 및 맞춤 가중치 시나리오 지원
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from .personalization import validate_and_normalize_weights

BASELINE_WEIGHTS: Dict[str, float] = {
    "demand": 0.30,
    "target_fit": 0.20,
    "competition": 0.15,
    "accessibility": 0.15,
    "parking": 0.10,
    "industry_fit": 0.10,
}

def to_percentile(series: pd.Series, ascending: bool = True) -> pd.Series:
    """
    주어진 시리즈를 0.0 ~ 100.0 범위의 균등 백분위수(Percentile Rank)로 변환합니다.
    - ascending=True: 값이 클수록 100점에 근접
    - ascending=False: 값이 작을수록 100점에 근접 (비용 지표)
    """
    n = len(series)
    if n <= 1:
        return pd.Series(50.0, index=series.index)
    
    # 중복값 평균 랭크 부여
    rank = series.rank(method="average", ascending=ascending)
    pct = ((rank - 1.0) / (n - 1.0) * 100.0).round(2)
    return pct.clip(0.0, 100.0)

def calculate_component_scores(df_feat: pd.DataFrame) -> pd.DataFrame:
    """
    피처 데이터프레임으로부터 6대 핵심 컴포넌트 점수를 산출합니다.
    반환되는 모든 점수는 0.0 ~ 100.0 범위입니다.
    """
    df = df_feat.copy()
    
    # 1. Demand Score (배후 수요 점수)
    # - 총인구(35%), 인구밀도(25%), 대중교통 승하차량(20%), 총점포수(20%)
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
    
    # 2. Target Fit Score (타깃 고객 적합도 점수)
    # - 타깃 고객 비중(60%) + 타깃 고객 절대 인구 규모(40%)
    p_tgt_ratio = to_percentile(df["target_ratio"])
    p_tgt_pop = to_percentile(df["target_pop"])
    
    target_fit_score = (
        0.60 * p_tgt_ratio +
        0.40 * p_tgt_pop
    ).round(2)
    
    # 3. Competition Score (경쟁 환경 기회 점수)
    # - 배후 타깃인구 대비 점포수(점포당 타깃인구수, 50% - 높을수록 높은 점수)
    # - 반경 300m 내 미크로 직접 경쟁점포수(50% - 낮을수록 과밀경쟁 회피)
    p_cap_opp = to_percentile(df["target_pop_per_store"])
    p_comp_penalty = to_percentile(df["cat_avg_comp_300m"], ascending=False)
    
    competition_score = (
        0.50 * p_cap_opp +
        0.50 * p_comp_penalty
    ).round(2)
    
    # 4. Accessibility Score (대중교통 접근성 점수)
    # - 최인접 역 평균 거리(50%, 가까울수록 우수)
    # - 역세권(500m 이내) 점포 비율(30%)
    # - 관내 역사 일평균 승하차 유동량(20%)
    p_sub_dist = to_percentile(df["cat_avg_subway_dist"], ascending=False)
    p_sub_zone = to_percentile(df["cat_ratio_subway"])
    p_sub_flow = to_percentile(df["dong_daily_ridership"])
    
    accessibility_score = (
        0.50 * p_sub_dist +
        0.30 * p_sub_zone +
        0.20 * p_sub_flow
    ).round(2)
    
    # 5. Parking Score (주차 공급 지표 점수)
    # *주의: 고객 전용 무료주차장이 아닌 건물 부설주차장 수용능력 proxy 지표임
    # - 반경 300m 내 평균 부설주차면수(50%)
    # - 점포당 부설주차면수(30%)
    # - 행정동 총 부설주차면수(20%)
    p_park_300m = to_percentile(df["cat_avg_parking_300m"])
    p_park_per_store = to_percentile(df["parking_capacity_per_store"])
    p_park_total = to_percentile(df["dong_total_parking_capacity"])
    
    parking_score = (
        0.50 * p_park_300m +
        0.30 * p_park_per_store +
        0.20 * p_park_total
    ).round(2)
    
    # 6. Industry Fit Score (업종 특화도)
    # 동일 업종을 행정동 간 비교할 때 LQ는 업종 비중의 상수배이므로,
    # 동일 정보를 이중 반영하지 않고 LQ 백분위만 사용한다.
    p_lq = to_percentile(df["location_quotient"])
    industry_fit_score = p_lq.round(2)
    
    # 컴포넌트 점수 컬럼 결합
    df["demand_score"] = demand_score.clip(0.0, 100.0)
    df["target_fit_score"] = target_fit_score.clip(0.0, 100.0)
    df["competition_score"] = competition_score.clip(0.0, 100.0)
    df["accessibility_score"] = accessibility_score.clip(0.0, 100.0)
    df["parking_score"] = parking_score.clip(0.0, 100.0)
    df["industry_fit_score"] = industry_fit_score.clip(0.0, 100.0)
    
    return df

def compute_total_score(
    df_scored: pd.DataFrame,
    weights: Optional[Dict[str, float]] = None
) -> pd.DataFrame:
    """
    각 컴포넌트 점수를 가중합산하여 0~100점의 최종 total_score를 산출합니다.
    """
    # Validate missing, negative, non-numeric and non-finite values before use.
    w_norm = validate_and_normalize_weights(weights)
    
    total = (
        w_norm["demand"] * df_scored["demand_score"] +
        w_norm["target_fit"] * df_scored["target_fit_score"] +
        w_norm["competition"] * df_scored["competition_score"] +
        w_norm["accessibility"] * df_scored["accessibility_score"] +
        w_norm["parking"] * df_scored["parking_score"] +
        w_norm["industry_fit"] * df_scored["industry_fit_score"]
    ).round(2)
    
    df_scored["total_score"] = total.clip(0.0, 100.0)
    return df_scored
