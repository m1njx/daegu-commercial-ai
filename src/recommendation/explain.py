# -*- coding: utf-8 -*-
"""
src/recommendation/explain.py

실제 데이터 기반 추천 사유 및 위험 요인 자동 생성(Explainability) 모듈
- Canonical Unified Explanation Engine: 3대 모델(Baseline, Improved, Enhanced) 설명 로직 단일화
- 거짓/허위 문장 생성 방지: 실제 피처 수치와 백분위수에 근거한 문장만 조합
- F02 Fix: 타깃 인구 비중 vs 절대 인구 규모 근거 분리 및 전체 타깃 비중 표현 배제
- F04 Fix: 모델별 교통 설명 엄격 분리 (철도 단독 모델에 버스 언급 원천 차단)
- F05 Fix: 관내 역 좌표 없는 행정동 중립 용어 통일
"""

from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np


def build_canonical_explanation(
    row: pd.Series,
    metadata: Dict[str, Any],
    model_type: str = "enhanced",
) -> Dict[str, Any]:
    """
    단일 추천 행정동에 대해 실제 수치 데이터 기반 일관된 추천 사유 및 주의사항을 생성합니다.
    (Phase 26 Canonical Deduplicated Explanation Engine)

    Parameters:
    - row: 행정동별 지표 및 컴포넌트 점수를 담은 Series
    - metadata: industry_label, target_demographic_label, target_demographic 등의 메타데이터
    - model_type: 'baseline', 'improved', 'enhanced' 중 선택
    """
    adm_nm = str(row.get("adm_nm", ""))
    short_nm = adm_nm.split()[-1] if adm_nm else ""
    ind_label = str(metadata.get("industry_label", "해당 업종"))
    tgt_label = str(metadata.get("target_demographic_label", "타깃 고객"))
    tgt_query = str(metadata.get("target_demographic", "")).strip()
    cat_cnt = int(row.get("cat_store_count", 0)) if pd.notnull(row.get("cat_store_count")) else 0
    rank = int(row.get("rank", 0))
    total_score = float(row.get("total_score", 0.0))

    strengths: List[str] = []
    cautions: List[str] = []

    # 1. 상권 형성 상태 분류 (Improved 및 Enhanced 모델)
    market_status = str(row.get("market_status", "해당 업종 점포 확인 지역"))
    if model_type in ("improved", "enhanced"):
        if bool(row.get("is_unentered", False)) or cat_cnt == 0:
            cautions.append(
                f"해당 업종 점포 미확인 지역 주의: 관내 {ind_label} 점포가 {cat_cnt}개소로 집계된 지역입니다. "
                f"관측된 경쟁점포는 적지만 실제 수요 부재 가능성이 있으므로 "
                f"창업 전 현장 상권 실사 및 인허가 요건 검토가 필수적입니다."
            )
        else:
            strengths.append(
                f"업종 점포 분포 확인: 관내 {ind_label} 점포 {cat_cnt}개소가 데이터에서 확인됩니다."
            )

    # 2. Target Fit (F02 Fix: 타깃 인구 비중 vs 절대 인구 규모 근거 분리)
    if float(row.get("target_fit_score", 0.0)) >= 65.0:
        tgt_pop = int(row.get("target_pop", row.get("pop_total", 0)))
        if tgt_query in ("전체", "전연령", "all") or "전체" in tgt_label:
            # 전체 인구: 비중은 100%이므로 비중 언급 금지, 절대 주민등록 인구 규모만 기술
            strengths.append(
                f"{tgt_label} 대상 규모: 주민등록 인구 약 {tgt_pop:,}명으로 비교 대상 행정동 중 인구 규모가 큰 편입니다."
            )
        else:
            tgt_pct = float(row.get("target_ratio", 0.0)) * 100.0
            p_ratio = row.get("target_ratio_pct", None)
            p_pop = row.get("target_pop_pct", None)

            if p_ratio is not None and p_pop is not None and pd.notnull(p_ratio) and pd.notnull(p_pop):
                p_ratio_f = float(p_ratio)
                p_pop_f = float(p_pop)
                if p_ratio_f >= 65.0 and p_pop_f >= 65.0:
                    strengths.append(
                        f"{tgt_label} 비중 및 규모: 관내 {tgt_label} 비중이 {tgt_pct:.1f}%(약 {tgt_pop:,}명)로 비중과 인구 규모 모두 상대적으로 높게 관측됩니다."
                    )
                elif p_ratio_f >= 65.0:
                    strengths.append(
                        f"{tgt_label} 비중: 관내 {tgt_label} 비중이 {tgt_pct:.1f}%(약 {tgt_pop:,}명)로 상대적으로 높게 관측됩니다."
                    )
                elif p_pop_f >= 65.0:
                    strengths.append(
                        f"{tgt_label} 규모: 관내 {tgt_label} 인구가 약 {tgt_pop:,}명으로 비교 대상 행정동 중 인구 규모가 상대적으로 큰 편입니다."
                    )
                else:
                    strengths.append(
                        f"{tgt_label} 적합도: 관내 {tgt_label} 비중 {tgt_pct:.1f}%(약 {tgt_pop:,}명)로 타깃 적합도 지표가 상대적으로 양호하게 산출됩니다."
                    )
            else:
                strengths.append(
                    f"{tgt_label} 비중: 관내 {tgt_label} 비중이 {tgt_pct:.1f}%(약 {tgt_pop:,}명)로 상대적으로 높게 관측됩니다."
                )

    # 3. Accessibility (F04 Fix: 모델별 교통 데이터 엄격 분리 & F05 Fix: 중립 용어)
    access_score = float(row.get("accessibility_score", 0.0))
    if access_score >= 65.0:
        if model_type == "enhanced":
            sub_flow = float(row.get("dong_daily_ridership", 0.0))
            station_cnt = int(row.get("dong_station_count", 0))
            bus_flow = float(row.get("dong_daily_bus_total", 0.0))
            bus_stops = int(row.get("dong_bus_stop_count", 0))
            bus_dist = float(row.get("avg_dist_to_bus_m", 0.0))

            if bus_flow > 0 and station_cnt > 0:
                strengths.append(
                    f"대중교통 접근성 우수: 도시철도 접근성(역 일평균 승하차 {sub_flow:,.0f}명)뿐 아니라 "
                    f"일평균 버스 승하차({bus_flow:,.0f}명)와 정류소({bus_stops}개소, 평균 {bus_dist:.0f}m) 접근성이 함께 높아 "
                    f"대중교통 접근성 점수({access_score:.1f}점)가 높게 평가되었습니다."
                )
            elif bus_flow > 0 and station_cnt == 0:
                strengths.append(
                    f"시내버스 접근성 지표: 관내 도시철도 역 좌표는 없으나 관내 시내버스 정류소 {bus_stops}개소(평균 {bus_dist:.0f}m), "
                    f"일평균 버스 승하차 {bus_flow:,.0f}명이며 접근성 점수는 {access_score:.1f}점입니다."
                )
            else:
                sub_dist = float(row.get("cat_avg_subway_dist", 0.0))
                flow_str = f", 역 일평균 승하차 {sub_flow:,.0f}명" if sub_flow > 0 else ""
                strengths.append(
                    f"도시철도 접근성 지표: 최인접 도시철도역 평균 거리 {sub_dist:.0f}m{flow_str}으로 접근성 지표가 상대적으로 높습니다."
                )
        else:
            # Baseline & Improved: 도시철도 단독 모델 -> 버스 언급 금지
            sub_dist = float(row.get("cat_avg_subway_dist", 0.0))
            sub_flow = float(row.get("dong_daily_ridership", 0.0))
            flow_str = f", 관내 도시철도 일평균 승하차 인원 {sub_flow:,.0f}명" if sub_flow > 0 else ""
            strengths.append(
                f"도시철도 접근성 지표: 지하철역 평균 거리 {sub_dist:.0f}m{flow_str}으로 접근성 지표가 상대적으로 높습니다."
            )

    # 4. Demand
    if float(row.get("demand_score", 0.0)) >= 65.0:
        pop_tot = int(row.get("pop_total", 0))
        stores = int(row.get("total_stores", 0))
        strengths.append(
            f"배후 규모 참고 지표: 주민등록 인구 {pop_tot:,}명과 총 점포수 {stores:,}개소가 관측됩니다."
        )

    # 5. Industry Fit (LQ)
    if (float(row.get("industry_fit_score", 0.0)) >= 65.0 and cat_cnt > 0
            and float(row.get("location_quotient", 0.0)) >= 1.0):
        lq = float(row.get("location_quotient", 0.0))
        strengths.append(
            f"업종 비중 상대 우위: {ind_label} LQ가 {lq:.2f}(점포 {cat_cnt}개소)로 대구 평균 대비 해당 업종 비중이 상대적으로 높습니다."
        )

    # 6. Competition
    comp_score = float(row.get("competition_score", 0.0))
    if comp_score >= 65.0 and (model_type == "baseline" or cat_cnt > 0):
        pop_per = float(row.get("target_pop_per_store", 0.0))
        strengths.append(
            f"수요 대비 점포 분포 참고: 점포당 배후 타깃인구가 약 {pop_per:.0f}명으로 산출되며, 실제 수요는 현장 확인이 필요합니다."
        )

    # 7. 주의 / 위험 요인
    # Parking
    if float(row.get("parking_score", 0.0)) < 45.0:
        cap_per = float(row.get("parking_capacity_per_store", 0.0))
        if model_type == "enhanced":
            cautions.append(
                f"주차 인프라 제약: 점포당 부설주차면수가 {cap_per:.2f}면 수준으로 협소하여 차량 방문보다는 도보 및 대중교통 이용 고객 유치 전략이 권장됩니다."
            )
        else:
            cautions.append(
                f"주차 인프라 제약: 점포당 부설주차면수가 {cap_per:.2f}면 수준으로 협소하여 차량 방문객보다는 도보·대중교통 고객 타깃 전략이 필수적입니다."
            )

    # Competition Crowding
    comp_300 = float(row.get("cat_avg_comp_300m", 0.0))
    if comp_300 >= 10.0:
        cautions.append(
            f"근거리 동종업종 밀집 경쟁 주의: 반경 300m 내 동종 점포가 평균 {comp_300:.1f}개 밀집하여 차별화된 메뉴/서비스 경쟁력이 요구됩니다."
        )

    # Accessibility Caution
    if model_type == "enhanced":
        if access_score < 40.0:
            bus_flow = float(row.get("dong_daily_bus_total", 0.0))
            station_cnt = int(row.get("dong_station_count", 0))
            if station_cnt == 0:
                cautions.append(
                    f"대중교통 인프라 한계: 관내 도시철도 역 좌표가 없는 행정동이며 버스 일평균 승하차({bus_flow:,.0f}명)가 상대적으로 적어 대중교통 유입보다는 로컬 배후 주거 수요 중심 영업이 권장됩니다."
                )
            else:
                cautions.append(
                    f"대중교통 접근성 취약: 대중교통 접근성 점수가 {access_score:.1f}점으로 낮아 도보 유입 동선이나 대체 접근로 확보가 필요합니다."
                )
    else:
        if access_score < 40.0 and float(row.get("cat_avg_subway_dist", 0.0)) > 1000.0:
            sub_dist = float(row.get("cat_avg_subway_dist", 0.0))
            cautions.append(
                f"역세권 외곽 입지: 지하철역과의 평균 거리가 {sub_dist:.0f}m로 대중교통 접근성이 낮아 로컬 주거 배후 수요 중심의 영업이 적합합니다."
            )

    # 요약 문장 생성
    top_strength_text = strengths[0] if strengths else "복수 관측 지표를 종합해 상대적 입지 적합도를 산출했습니다."
    if model_type == "baseline":
        summary_sentence = (
            f"{short_nm}은(는) 종합 추천 점수 {total_score:.1f}점(순위: {rank}위)으로, {top_strength_text}"
        )
    elif model_type == "improved":
        summary_sentence = (
            f"{short_nm}은(는) [{market_status}]으로 종합 추천 점수 {total_score:.1f}점(순위: {rank}위)입니다. {top_strength_text}"
        )
    else:  # enhanced
        summary_sentence = (
            f"{short_nm}은(는) [{market_status}]으로 종합 입지 적합도 {total_score:.2f}점(순위: {rank}위)입니다. {top_strength_text}"
        )

    out = {
        "adm_nm": adm_nm,
        "short_nm": short_nm,
        "rank": rank,
        "total_score": total_score,
        "summary_sentence": summary_sentence,
        "strengths": strengths,
        "cautions": cautions,
    }
    if model_type in ("improved", "enhanced"):
        out["market_status"] = market_status
    return out


def generate_explanation(row: pd.Series, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    단일 추천 행정동에 대해 Phase 5 기준선 모델 사유를 생성합니다.
    (Canonical engine 호출)
    """
    return build_canonical_explanation(row, metadata, model_type="baseline")
