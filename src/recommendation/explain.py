# -*- coding: utf-8 -*-
"""
src/recommendation/explain.py

실제 데이터 기반 추천 사유 및 위험 요인 자동 생성(Explainability) 모듈
- 거짓/허위 문장 생성 방지: 실제 피처 수치와 백분위수에 근거한 문장만 조합
- 강점 요인(Strengths) 및 주의/위험 요인(Risk Factors) 동시 제시
"""

import pandas as pd
from typing import Dict, Any, List

def generate_explanation(row: pd.Series, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    단일 추천 행정동에 대해 실제 수치 데이터를 기반으로 추천 사유를 생성합니다.
    """
    adm_nm = row.get("adm_nm", "")
    short_nm = adm_nm.split()[-1] if adm_nm else ""
    ind_label = metadata.get("industry_label", "해당 업종")
    tgt_label = metadata.get("target_demographic_label", "타깃 고객")
    
    strengths: List[str] = []
    cautions: List[str] = []
    
    # 1. 컴포넌트별 강점/약점 분석
    comp_scores = {
        "demand": ("배후 수요", row.get("demand_score", 0)),
        "target_fit": ("타깃 고객 적합도", row.get("target_fit_score", 0)),
        "competition": ("경쟁 환경 기회", row.get("competition_score", 0)),
        "accessibility": ("대중교통 접근성", row.get("accessibility_score", 0)),
        "parking": ("주차 공급 여건", row.get("parking_score", 0)),
        "industry_fit": ("업종 특화도", row.get("industry_fit_score", 0)),
    }
    
    # 2. 강점 요인 (점수가 65점 이상인 컴포넌트 중 상위 항목)
    # Target Fit
    if row.get("target_fit_score", 0) >= 65:
        tgt_pct = row.get("target_ratio", 0) * 100.0
        tgt_pop = int(row.get("target_pop", 0))
        strengths.append(
            f"**{tgt_label} 집적 우수**: 관내 {tgt_label} 비중이 {tgt_pct:.1f}%(약 {tgt_pop:,}명)에 달해 핵심 고객 기반이 매우 탄탄합니다."
        )
        
    # Accessibility
    if row.get("accessibility_score", 0) >= 65:
        sub_dist = row.get("cat_avg_subway_dist", 0)
        sub_flow = row.get("dong_daily_ridership", 0)
        flow_str = f", 관내 도시철도 일평균 승하차 인원 {sub_flow:,.0f}명" if sub_flow > 0 else ""
        strengths.append(
            f"**대중교통 접근성 탁월**: 지하철역 평균 거리 {sub_dist:.0f}m{flow_str}으로 도보 고객 유입이 용이합니다."
        )
        
    # Demand
    if row.get("demand_score", 0) >= 65:
        pop_tot = int(row.get("pop_total", 0))
        stores = int(row.get("total_stores", 0))
        strengths.append(
            f"**풍부한 기초 상권 수요**: 배후 주민등록 인구 {pop_tot:,}명과 총 점포수 {stores:,}개소로 상권 활성도가 높습니다."
        )
        
    # Industry Fit (LQ)
    if row.get("industry_fit_score", 0) >= 65 and row.get("cat_store_count", 0) > 0:
        lq = row.get("location_quotient", 0)
        cnt = int(row.get("cat_store_count", 0))
        strengths.append(
            f"**동종 업종 시너지**: {ind_label} 특화도(LQ) {lq:.2f}(점포 {cnt}개소)로 해당 업종의 소비 인지도 및 집적 효과가 형성되어 있습니다."
        )
        
    # Competition
    if row.get("competition_score", 0) >= 65:
        pop_per = row.get("target_pop_per_store", 0)
        strengths.append(
            f"**수요 대비 경쟁 여유도 우수**: 점포당 배후 타깃인구가 약 {pop_per:.0f}명으로 미포화 성장 기회가 존재합니다."
        )

    # 3. 주의/위험 요인 (점수가 45점 미만인 항목)
    # Parking
    if row.get("parking_score", 0) < 45:
        cap_per = row.get("parking_capacity_per_store", 0)
        cautions.append(
            f"**주차 인프라 제약**: 점포당 부설주차면수가 {cap_per:.2f}면 수준으로 협소하여 차량 방문객보다는 도보·대중교통 고객 타깃 전략이 필수적입니다."
        )
        
    # Competition Crowding
    comp_300 = row.get("cat_avg_comp_300m", 0)
    if comp_300 >= 10.0:
        cautions.append(
            f"**근거리 동종업종 밀집 경쟁 주의**: 반경 300m 내 동종 점포가 평균 {comp_300:.1f}개 밀집하여 차별화된 메뉴/서비스 경쟁력이 요구됩니다."
        )
        
    # Subway Distance
    if row.get("accessibility_score", 0) < 40 and row.get("cat_avg_subway_dist", 0) > 1000:
        sub_dist = row.get("cat_avg_subway_dist", 0)
        cautions.append(
            f"**역세권 외곽 입지**: 지하철역과의 평균 거리가 {sub_dist:.0f}m로 대중교통 접근성이 낮아 로컬 주거 배후 수요 중심의 영업이 적합합니다."
        )
        
    # 요약 문장 생성
    top_strength_text = strengths[0].replace("**", "") if strengths else "균형 잡힌 상권 인프라를 보유하고 있습니다."
    summary_sentence = (
        f"{short_nm}은(는) 종합 추천 점수 {row.get('total_score', 0):.1f}점(순위: {row.get('rank', 0)}위)으로, "
        f"{top_strength_text}"
    )
    
    # UI consumers should never need to understand Markdown to display safely.
    strengths = [item.replace("**", "") for item in strengths]
    cautions = [item.replace("**", "") for item in cautions]

    return {
        "adm_nm": adm_nm,
        "short_nm": short_nm,
        "rank": int(row.get("rank", 0)),
        "total_score": float(row.get("total_score", 0)),
        "summary_sentence": summary_sentence,
        "strengths": strengths,
        "cautions": cautions,
    }
