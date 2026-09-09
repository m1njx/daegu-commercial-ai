# -*- coding: utf-8 -*-
"""
src/recommendation/transit_enhanced.py

시내버스 승하차 및 정류소 데이터를 통합한 대중교통 접근성(Accessibility) 고도화 모듈
- 기존 도시철도 중심 접근성(Baseline)과 버스 연계 접근성(Bus-Enhanced)의 병렬 지원
- 교통수단별 데이터 단위 왜곡 방지를 위한 개별 백분위 정규화(Percentile Rank) 원칙 준수
- 후보 공식 A(80/20), B(70/30), C(60/40) 및 실험 지원
- 기존 6대 컴포넌트 가중치(Demand 30%, Target 20%, Comp 15%, Access 15%, Park 10%, Ind 10%) 및
  Phase 6 0-store 미진입 상권 보정(alpha=0.50) 완벽 호환
"""

from typing import Dict, Any, Optional, Tuple, List
import pandas as pd
import numpy as np

from src.recommendation.scoring import to_percentile, BASELINE_WEIGHTS
from src.recommendation.personalization import validate_and_normalize_weights
from src.recommendation.ranking import rank_locations
from src.recommendation.improved import (
    DEFAULT_MIN_STORES,
    DEFAULT_MIN_TOTAL_STORES,
    DEFAULT_DISCOUNT_FACTOR,
)

# Accessibility 후보 가중치 (Subway vs Bus)
TRANSIT_CANDIDATES = {
    "baseline": {"subway_weight": 1.00, "bus_weight": 0.00, "label": "Baseline (철도 100%)"},
    "candidate_a": {"subway_weight": 0.80, "bus_weight": 0.20, "label": "Candidate A (철도 80% + 버스 20%)"},
    "candidate_b": {"subway_weight": 0.70, "bus_weight": 0.30, "label": "Candidate B (철도 70% + 버스 30%)"},
    "candidate_c": {"subway_weight": 0.60, "bus_weight": 0.40, "label": "Candidate C (철도 60% + 버스 40%)"},
}

def calculate_bus_accessibility_score(df: pd.DataFrame) -> pd.Series:
    """
    행정동별 버스 접근성 점수 (0~100) 산출:
    - 버스 일평균 이용자수 백분위 (50%)
    - 최인접 버스 정류소 거리 역백분위 (30%, 가까울수록 우수)
    - 면적당 버스 정류소 밀도 백분위 (20%, 높을수록 접근 용이)
    """
    p_bus_flow = to_percentile(df["dong_daily_bus_total"])
    p_bus_dist = to_percentile(df["avg_dist_to_bus_m"], ascending=False)
    p_bus_density = to_percentile(df["dong_bus_stop_density"])
    
    bus_score = (
        0.50 * p_bus_flow +
        0.30 * p_bus_dist +
        0.20 * p_bus_density
    ).round(2)
    return bus_score

def calculate_enhanced_transit_accessibility(
    df: pd.DataFrame,
    candidate: str = "candidate_b"
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    지하철 접근성, 버스 접근성, 그리고 가중합산 종합 대중교통 접근성을 반환합니다.
    """
    # 1. 기존 철도 접근성 (Phase 5/7 Source of Truth)
    p_sub_dist = to_percentile(df["cat_avg_subway_dist"], ascending=False)
    p_sub_zone = to_percentile(df["cat_ratio_subway"])
    p_sub_flow = to_percentile(df["dong_daily_ridership"])
    
    subway_score = (
        0.50 * p_sub_dist +
        0.30 * p_sub_zone +
        0.20 * p_sub_flow
    ).round(2)
    
    # 2. 버스 접근성
    if "dong_daily_bus_total" in df.columns:
        bus_score = calculate_bus_accessibility_score(df)
    else:
        bus_score = pd.Series(50.0, index=df.index)
        
    # 3. 가중 결합
    cand_cfg = TRANSIT_CANDIDATES.get(candidate, TRANSIT_CANDIDATES["candidate_b"])
    w_sub = cand_cfg["subway_weight"]
    w_bus = cand_cfg["bus_weight"]
    
    combined_score = (w_sub * subway_score + w_bus * bus_score).round(2)
    return combined_score, subway_score, bus_score

def calculate_enhanced_scores(
    df_feat: pd.DataFrame,
    weights: Optional[Dict[str, float]] = None,
    candidate: str = "candidate_b",
    is_improved: bool = True,
    min_stores: int = DEFAULT_MIN_STORES,
    min_total_stores: int = DEFAULT_MIN_TOTAL_STORES,
    discount_factor: float = DEFAULT_DISCOUNT_FACTOR,
) -> pd.DataFrame:
    """
    버스 데이터가 결합된 통합 피처 데이터프레임으로부터 6대 컴포넌트 점수 및 총점을 계산합니다.
    - is_improved=True: Phase 6 alpha=0.50 0-store 보정 적용
    - is_improved=False: Phase 5 Baseline 원본 계산 적용
    """
    df = df_feat.copy()
    
    # 1. Base Component Scoring
    # (1) Demand Score (기존 유지)
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
    
    # (2) Target Fit Score (기존 유지)
    p_tgt_ratio = to_percentile(df["target_ratio"])
    p_tgt_pop = to_percentile(df["target_pop"])
    
    target_fit_score = (
        0.60 * p_tgt_ratio +
        0.40 * p_tgt_pop
    ).round(2)
    
    # (3) Competition Score
    p_cap_opp = to_percentile(df["target_pop_per_store"])
    p_comp_penalty = to_percentile(df["cat_avg_comp_300m"], ascending=False)
    
    raw_comp_score = (
        0.50 * p_cap_opp +
        0.50 * p_comp_penalty
    ).round(2)
    
    if is_improved:
        is_unentered = (df["cat_store_count"] < min_stores) | (df["total_stores"] < min_total_stores)
        competition_score = raw_comp_score.copy()
        competition_score.loc[is_unentered] = (raw_comp_score.loc[is_unentered] * discount_factor).round(2)
    else:
        is_unentered = pd.Series(False, index=df.index)
        competition_score = raw_comp_score.copy()
        
    # (4) Enhanced Accessibility Score (지하철 + 버스 결합)
    access_score, sub_score, bus_score = calculate_enhanced_transit_accessibility(df, candidate=candidate)
    
    # (5) Parking Score (기존 유지)
    p_park_300m = to_percentile(df["cat_avg_parking_300m"])
    p_park_per_store = to_percentile(df["parking_capacity_per_store"])
    p_park_total = to_percentile(df["dong_total_parking_capacity"])
    
    parking_score = (
        0.50 * p_park_300m +
        0.30 * p_park_per_store +
        0.20 * p_park_total
    ).round(2)
    
    # (6) Industry Fit Score (기존 유지)
    p_lq = to_percentile(df["location_quotient"])
    p_share = to_percentile(df["store_share_in_dong"])
    
    industry_fit_score = (
        0.60 * p_lq +
        0.40 * p_share
    ).round(2)
    
    # 2. Total Score Computation
    w = validate_and_normalize_weights(weights if weights is not None else BASELINE_WEIGHTS)
    
    total_score = (
        w["demand"] * demand_score +
        w["target_fit"] * target_fit_score +
        w["competition"] * competition_score +
        w["accessibility"] * access_score +
        w["parking"] * parking_score +
        w["industry_fit"] * industry_fit_score
    ).round(2)
    
    # 결과 데이터프레임 구성
    result = df.copy()
    result["demand_score"] = demand_score
    result["target_fit_score"] = target_fit_score
    result["competition_score"] = competition_score
    result["raw_competition_score"] = raw_comp_score
    result["accessibility_score"] = access_score
    result["subway_accessibility_score"] = sub_score
    result["bus_accessibility_score"] = bus_score
    result["parking_score"] = parking_score
    result["industry_fit_score"] = industry_fit_score
    result["total_score"] = total_score
    result["is_unentered"] = is_unentered
    result["transit_candidate"] = candidate

    if is_improved:
        market_status = np.where(
            ~is_unentered,
            "검증된 상권",
            np.where(df["cat_store_count"] == 0, "미진입 상권 (점포 0개)", "미검증 소규모 상권")
        )
    else:
        market_status = pd.Series("기준선 분석 상권", index=df.index)
    result["market_status"] = market_status
    
    return result


def generate_enhanced_explanation(row: pd.Series, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Candidate B 대중교통(도시철도+시내버스) 통합 모델 기반 추천 사유 및 주의 요인 생성.
    - 실제 수치에 기반한 Data-Grounded 생성 (허위/과장 문구 배제)
    - 금지어 완전 배제: '실제 유동인구', '방문객 수', '고객 수', '소비자 수' 미사용
    - 정확한 승하차 표현: '도시철도 일평균 승하차 인원', '시내버스 일평균 승하차 인원'
    """
    adm_nm = row.get("adm_nm", "")
    short_nm = adm_nm.split()[-1] if adm_nm else ""
    ind_label = metadata.get("industry_label", "해당 업종")
    tgt_label = metadata.get("target_demographic_label", "타깃 고객")
    cat_cnt = int(row.get("cat_store_count", 0))
    market_status = str(row.get("market_status", "검증된 상권"))
    
    strengths: List[str] = []
    cautions: List[str] = []
    
    # 1. Target Fit
    if row.get("target_fit_score", 0) >= 65:
        tgt_pct = row.get("target_ratio", 0) * 100.0
        tgt_pop = int(row.get("target_pop", 0))
        strengths.append(
            f"**{tgt_label} 집적 우수**: 관내 {tgt_label} 비중이 {tgt_pct:.1f}%(약 {tgt_pop:,}명)에 달해 핵심 고객 기반이 탄탄합니다."
        )
        
    # 2. Enhanced Accessibility (Candidate B: Subway 70% + Bus 30%)
    access_score = row.get("accessibility_score", 0)
    if access_score >= 65:
        sub_flow = row.get("dong_daily_ridership", 0)
        station_cnt = int(row.get("dong_station_count", 0))
        bus_flow = row.get("dong_daily_bus_total", 0)
        bus_stops = int(row.get("dong_bus_stop_count", 0))
        bus_dist = row.get("avg_dist_to_bus_m", 0)
        
        if bus_flow > 0 and station_cnt > 0:
            strengths.append(
                f"**대중교통 접근성 우수**: 도시철도 접근성(역 일평균 승하차 {sub_flow:,.0f}명)뿐 아니라 일평균 버스 승하차({bus_flow:,.0f}명)와 정류소({bus_stops}개소, 평균 {bus_dist:.0f}m) 접근성이 함께 높아 대중교통 접근성 점수({access_score:.1f}점)가 높게 평가되었습니다."
            )
        elif bus_flow > 0 and station_cnt == 0:
            strengths.append(
                f"**시내버스 대중교통망 우수**: 도시철도역은 없으나 관내 시내버스 정류소 {bus_stops}개소(평균 {bus_dist:.0f}m) 및 일평균 버스 승하차 {bus_flow:,.0f}명의 탄탄한 버스 접근성({access_score:.1f}점)을 보유하고 있습니다."
            )
        else:
            sub_dist = row.get("cat_avg_subway_dist", 0)
            flow_str = f", 역 일평균 승하차 {sub_flow:,.0f}명" if sub_flow > 0 else ""
            strengths.append(
                f"**대중교통 접근성 탁월**: 최인접 도시철도역 평균 거리 {sub_dist:.0f}m{flow_str}으로 대중교통 접근성이 우수합니다."
            )
            
    # 3. Demand
    if row.get("demand_score", 0) >= 65:
        pop_tot = int(row.get("pop_total", 0))
        stores = int(row.get("total_stores", 0))
        strengths.append(
            f"**풍부한 기초 상권 수요**: 배후 주민등록 인구 {pop_tot:,}명과 총 점포수 {stores:,}개소로 상권 활성도가 높습니다."
        )
        
    # 4. Industry Fit (LQ)
    if row.get("industry_fit_score", 0) >= 65 and cat_cnt > 0:
        lq = row.get("location_quotient", 0)
        strengths.append(
            f"**동종 업종 시너지**: {ind_label} 특화도(LQ) {lq:.2f}(점포 {cat_cnt}개소)로 해당 업종의 소비 인지도 및 집적 효과가 형성되어 있습니다."
        )
        
    # 5. Competition
    if row.get("competition_score", 0) >= 65 and cat_cnt > 0:
        pop_per = row.get("target_pop_per_store", 0)
        strengths.append(
            f"**수요 대비 경쟁 여유도 우수**: 점포당 배후 타깃인구가 약 {pop_per:.0f}명으로 미포화 성장 기회가 존재합니다."
        )
        
    # 6. 주의 / 확인 필요 요인
    if row.get("parking_score", 0) < 45:
        cap_per = row.get("parking_capacity_per_store", 0)
        cautions.append(
            f"**주차 인프라 제약**: 점포당 부설주차면수가 {cap_per:.2f}면 수준으로 협소하여 차량 방문보다는 도보 및 대중교통 이용 고객 유치 전략이 권장됩니다."
        )
        
    comp_300 = row.get("cat_avg_comp_300m", 0)
    if comp_300 >= 10.0:
        cautions.append(
            f"**미크로 밀집 경쟁 주의**: 반경 300m 내 동종 점포가 평균 {comp_300:.1f}개 밀집하여 차별화된 메뉴/서비스 경쟁력이 요구됩니다."
        )
        
    if access_score < 40:
        bus_flow = row.get("dong_daily_bus_total", 0)
        station_cnt = int(row.get("dong_station_count", 0))
        if station_cnt == 0:
            cautions.append(
                f"**대중교통 인프라 한계**: 도시철도 미경유 지역이며 버스 일평균 승하차({bus_flow:,.0f}명)가 상대적으로 적어 대중교통 유입보다는 로컬 배후 주거 수요 중심 영업이 권장됩니다."
            )
        else:
            cautions.append(
                f"**대중교통 접근성 취약**: 대중교통 접근성 점수가 {access_score:.1f}점으로 낮아 도보 유입 동선이나 대체 접근로 확보가 필요합니다."
            )
            
    top_strength_text = strengths[0].replace("**", "") if strengths else "균형 잡힌 상권 인프라를 보유하고 있습니다."
    summary_sentence = (
        f"{short_nm}은(는) [{market_status}]으로 종합 입지 적합도 {row.get('total_score', 0):.2f}점(순위: {int(row.get('rank', 0))}위)입니다. "
        f"{top_strength_text}"
    )
    
    clean_strengths = [item.replace("**", "") for item in strengths]
    clean_cautions = [item.replace("**", "") for item in cautions]
    
    return {
        "adm_nm": adm_nm,
        "short_nm": short_nm,
        "rank": int(row.get("rank", 0)),
        "total_score": float(row.get("total_score", 0)),
        "market_status": market_status,
        "summary_sentence": summary_sentence,
        "strengths": clean_strengths,
        "cautions": clean_cautions,
    }
