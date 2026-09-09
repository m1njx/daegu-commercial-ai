# -*- coding: utf-8 -*-
"""
src/recommendation/improved.py

개선(IMPROVED) 추천 모델 및 0개 점포 미진입 상권 보정 모듈
- Phase 5 Baseline 모델을 보존하면서, 0개 점포 지역의 왜곡(무경쟁 착시 현상)을 보정
- "검증된 상권(점포>=1)"과 "미진입/시장 미형성 상권(점포 0개)"을 명확히 구분
- 시장 형성 리스크 할인 계수(Market Readiness Discount) 및 임계값 민감도 지원
- 설명 가능성(Explainability)에 상권 검증 상태 및 진입 리스크 명시
"""

from typing import Dict, Any, Optional, Tuple, List
import pandas as pd
import numpy as np

from src.recommendation.scoring import to_percentile, BASELINE_WEIGHTS
from src.recommendation.personalization import validate_and_normalize_weights
from src.recommendation.ranking import rank_locations

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
    if not isinstance(min_stores, (int, np.integer)) or min_stores < 0:
        raise ValueError("min_stores must be a non-negative integer")
    if not isinstance(min_total_stores, (int, np.integer)) or min_total_stores < 0:
        raise ValueError("min_total_stores must be a non-negative integer")
    try:
        discount_factor = float(discount_factor)
    except (TypeError, ValueError) as exc:
        raise ValueError("discount_factor must be a finite number between 0 and 1") from exc
    if not np.isfinite(discount_factor) or not 0.0 <= discount_factor <= 1.0:
        raise ValueError("discount_factor must be a finite number between 0 and 1")

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
    
    # (6) Industry Fit Score
    p_lq = to_percentile(df["location_quotient"])
    p_ind_share = to_percentile(df["store_share_in_dong"])
    
    industry_fit_score = (
        0.60 * p_lq +
        0.40 * p_ind_share
    ).round(2)
    
    # 2. 상권 형성 상태 분류 및 0개 점포 보정
    is_store_unentered = df["cat_store_count"] < min_stores
    is_scale_insufficient = df["total_stores"] < min_total_stores
    is_unentered = is_store_unentered | is_scale_insufficient
    
    market_status = np.where(
        ~is_unentered,
        "검증된 상권",
        np.where(df["cat_store_count"] == 0, "미진입 상권 (점포 0개)", "미검증 소규모 상권")
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
    - 상권 검증 상태(검증된 상권 vs 미진입 상권) 반영
    - 실제 수치 데이터 기반 강점 및 주의사항 도출
    """
    adm_nm = row.get("adm_nm", "")
    short_nm = adm_nm.split()[-1] if adm_nm else ""
    ind_label = metadata.get("industry_label", "해당 업종")
    tgt_label = metadata.get("target_demographic_label", "타깃 고객")
    market_status = row.get("market_status", "검증된 상권")
    cat_cnt = int(row.get("cat_store_count", 0))
    
    strengths: List[str] = []
    cautions: List[str] = []
    
    # 1. 상권 상태별 진단
    if row.get("is_unentered", False) or cat_cnt == 0:
        cautions.append(
            f"**미진입 상권 주의**: 관내 {ind_label} 점포가 {cat_cnt}개소(미진입)인 지역입니다. "
            f"경쟁점포가 적어 수치상 기회점수가 주어지나, 실제 상권 미형성 또는 수요 부재 위험이 있으므로 "
            f"창업 전 현장 상권 실사 및 인허가 요건 검토가 필수적입니다."
        )
    else:
        strengths.append(
            f"**검증된 업종 상권**: 관내 {ind_label} 점포 {cat_cnt}개소가 실운영 중인 검증된 상권입니다."
        )
        
    # 2. 강점 요인
    if row.get("target_fit_score", 0) >= 65:
        tgt_pct = row.get("target_ratio", 0) * 100.0
        tgt_pop = int(row.get("target_pop", 0))
        strengths.append(
            f"**{tgt_label} 집적 우수**: 관내 {tgt_label} 비중이 {tgt_pct:.1f}%(약 {tgt_pop:,}명)에 달해 핵심 고객 기반이 매우 탄탄합니다."
        )
        
    if row.get("accessibility_score", 0) >= 65:
        sub_dist = row.get("cat_avg_subway_dist", 0)
        sub_flow = row.get("dong_daily_ridership", 0)
        flow_str = f", 관내 도시철도 일평균 승하차 인원 {sub_flow:,.0f}명" if sub_flow > 0 else ""
        strengths.append(
            f"**대중교통 접근성 탁월**: 지하철역 평균 거리 {sub_dist:.0f}m{flow_str}으로 도보 고객 유입이 용이합니다."
        )
        
    if row.get("demand_score", 0) >= 65:
        pop_tot = int(row.get("pop_total", 0))
        stores = int(row.get("total_stores", 0))
        strengths.append(
            f"**풍부한 기초 상권 수요**: 배후 주민등록 인구 {pop_tot:,}명과 총 점포수 {stores:,}개소로 상권 활성도가 높습니다."
        )
        
    if row.get("industry_fit_score", 0) >= 65 and cat_cnt > 0:
        lq = row.get("location_quotient", 0)
        strengths.append(
            f"**동종 업종 시너지**: {ind_label} 특화도(LQ) {lq:.2f}(점포 {cat_cnt}개소)로 해당 업종의 소비 인지도 및 집적 효과가 형성되어 있습니다."
        )
        
    if row.get("competition_score", 0) >= 65 and cat_cnt > 0:
        pop_per = row.get("target_pop_per_store", 0)
        strengths.append(
            f"**수요 대비 경쟁 여유도 우수**: 점포당 배후 타깃인구가 약 {pop_per:.0f}명으로 미포화 성장 기회가 존재합니다."
        )
        
    # 3. 주의/위험 요인
    if row.get("parking_score", 0) < 45:
        cap_per = row.get("parking_capacity_per_store", 0)
        cautions.append(
            f"**주차 인프라 제약**: 점포당 부설주차면수가 {cap_per:.2f}면 수준으로 협소하여 차량 방문객보다는 도보·대중교통 고객 타깃 전략이 필수적입니다."
        )
        
    comp_300 = row.get("cat_avg_comp_300m", 0)
    if comp_300 >= 10.0:
        cautions.append(
            f"**근거리 동종업종 밀집 경쟁 주의**: 반경 300m 내 동종 점포가 평균 {comp_300:.1f}개 밀집하여 차별화된 메뉴/서비스 경쟁력이 요구됩니다."
        )
        
    if row.get("accessibility_score", 0) < 40 and row.get("cat_avg_subway_dist", 0) > 1000:
        sub_dist = row.get("cat_avg_subway_dist", 0)
        cautions.append(
            f"**역세권 외곽 입지**: 지하철역과의 평균 거리가 {sub_dist:.0f}m로 대중교통 접근성이 낮아 로컬 주거 배후 수요 중심의 영업이 적합합니다."
        )
        
    top_strength_text = strengths[0].replace("**", "") if strengths else "균형 잡힌 상권 인프라를 보유하고 있습니다."
    summary_sentence = (
        f"{short_nm}은(는) [{market_status}]으로 종합 추천 점수 {row.get('total_score', 0):.1f}점(순위: {row.get('rank', 0)}위)입니다. "
        f"{top_strength_text}"
    )
    
    # Keep the explanation API presentation-neutral for tables and non-Markdown UI.
    strengths = [item.replace("**", "") for item in strengths]
    cautions = [item.replace("**", "") for item in cautions]

    return {
        "adm_nm": adm_nm,
        "short_nm": short_nm,
        "rank": int(row.get("rank", 0)),
        "total_score": float(row.get("total_score", 0)),
        "market_status": market_status,
        "summary_sentence": summary_sentence,
        "strengths": strengths,
        "cautions": cautions,
    }
