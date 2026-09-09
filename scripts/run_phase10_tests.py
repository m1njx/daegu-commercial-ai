# -*- coding: utf-8 -*-
"""
scripts/run_phase10_tests.py

Phase 10: 제출용 Streamlit UI 최종 QA / Release Candidate 10대 자동화 테스트 스위트
1. App import 및 구문 컴파일 무결성 검증 (py_compile)
2. 서비스 공식 타이틀 및 팀명(말괄량이코물이) UI 표기 무결성 검증
3. 모델 선택기 3종 모드 정의, 레이블 정제 및 Candidate B 기본값 검증
4. Folium 맵 렌더링 무결성 검증 (get_root().render() 채택 및 노트북 경고 방지)
5. Top 5 컴팩트 카드 행정동 축약 표기(구/동 단위) 무결성 검증
6. 6대 데모 시나리오 Candidate B 1위 입지 및 점수 일관성 검증
7. UI 및 설명 텍스트 내 금지어(유동인구/방문객/10개 행정동 fallback 등) 완전 배제 검증
8. 150개 행정동 분석 데이터 CSV 내보내기 무결성 검증 (150행, UTF-8-SIG, 결측치 0)
9. Tab 3 모델 정량 비교 동적 스피어만 상관계수 및 벤치마크 안내 무결성 검증
10. 150개 행정동 전수 순위(1~150위) 및 점수(0~100) 유효성 무결성 검증
"""

import sys
import os
import py_compile
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

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
from src.recommendation.personalization import (
    WEIGHT_PRESETS,
    validate_and_normalize_weights,
)

def run_phase10_tests():
    print("=" * 70)
    print("PHASE 10: Streamlit UI 최종 QA / Release Candidate 10대 자동화 테스트 스위트")
    print("=" * 70)

    app_path = ROOT_DIR / "app" / "app.py"
    dong_path = ROOT_DIR / "data" / "processed" / "feature_mart" / "commercial_feature_mart_dong.parquet"
    store_path = ROOT_DIR / "data" / "processed" / "feature_mart" / "store_spatial_features.parquet"
    bus_path = PROCESSED_BUS_DIR / "daegu_bus_dong_features.parquet"

    # Test 1: App import 및 바이트코드 구문 컴파일 무결성 검증
    py_compile.compile(str(app_path), doraise=True)
    with open(app_path, "r", encoding="utf-8") as f:
        app_code = f.read()
    print("[PASS] Test 1: app/app.py 바이트코드 컴파일 무결성 검증 통과")

    # Test 2: 서비스 공식 타이틀 및 팀명(말괄량이코물이) UI 표기 검증
    assert "대구 소상공인 AI 상권·창업 입지 추천 서비스" in app_code, "공식 서비스 타이틀 누락"
    assert "말괄량이코물이" in app_code, "팀명 말괄량이코물이 누락"
    assert "팀 말괄량이코물이" in app_code, "배너/푸터 팀 말괄량이코물이 표기 누락"
    print("[PASS] Test 2: 공식 서비스 타이틀 및 팀명(말괄량이코물이) 표기 무결성 통과")

    # Test 3: 모델 선택기 3종 모드 정의, 정제된 레이블 및 Candidate B 기본값 검증
    assert 'MODEL_MODE_INTEGRATED = "통합 대중교통 모델 (권장 / 도시철도 70% + 시내버스 30%)"' in app_code
    assert 'MODEL_MODE_SUBWAY_IMPROVED = "도시철도 중심 모델 (도시철도 역세권 중심)"' in app_code
    assert 'MODEL_MODE_BASELINE = "초기 기준선 모델 (도시철도 단순 거리)"' in app_code
    assert "(Phase 7 IMPROVED)" not in app_code, "개발 단계 지르곤 (Phase 7 IMPROVED) 노출"
    assert "(Phase 5 BASELINE)" not in app_code, "개발 단계 지르곤 (Phase 5 BASELINE) 노출"
    assert "index=0" in app_code, "Candidate B 기본 인덱스 미지정"
    print("[PASS] Test 3: 모델 선택기 3종 정제 레이블 및 Candidate B 기본 선택 검증 통과")

    # Test 4: Folium 맵 렌더링 무결성 (get_root().render() 채택 검증)
    assert "map_html = compact_map.get_root().render()" in app_code, "Folium get_root().render() 미적용"
    assert 'hasattr(st, "iframe")' in app_code, "Streamlit iframe 호환 분기 누락"
    assert "compact_map._repr_html_()" not in app_code, "Jupyter _repr_html_() 잔존"
    print("[PASS] Test 4: Folium 맵 get_root().render() 채택 및 노트북 신뢰 경고 원천 차단 검증 통과")

    # Test 5: Top 5 컴팩트 카드 행정동 축약 표기(구/동 단위) 무결성 검증
    assert "compact_short = clean_markdown_to_html" in app_code, "컴팩트 카드 이름 축약 로직 누락"
    assert "adm_parts[1:]" in app_code, "행정동 앞단(대구광역시) 분리 로직 누락"
    assert 'title="{compact_name}"' in app_code, "마우스 호버 시 전체 행정동명 툴팁 제공 누락"
    print("[PASS] Test 5: Top 5 컴팩트 카드 구/동 축약 표기 및 전체 행정동 툴팁 검증 통과")

    # Test 6: 6대 데모 시나리오 Candidate B 1위 입지 및 점수 일관성 검증
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

    demo_scenarios = [
        ("카페", "2030", None, "신암4동", 77.75),
        ("한식", "전체", "배후 수요 집중형 (대형 매장/안정형)", "상인1동", 77.47),
        ("미용실", "2030", None, "칠성동", 75.45),
        ("학원", "10대", "타깃 고객 집중형 (트렌디/특화 소비)", "범어1동", 84.47),
        ("종합소매", "전체", None, "상인1동", 72.22),
        ("숙박", "2030", None, "감삼동", 75.82),
    ]

    for ind, tgt, preset_key, exp_dong, exp_sc in demo_scenarios:
        f, _ = build_dong_industry_features(ind, tgt, df_dong, df_store)
        for col in bus_cols:
            f[col] = df_dong[col].values
        w = WEIGHT_PRESETS[preset_key] if preset_key else BASELINE_WEIGHTS
        scored = calculate_enhanced_scores(f, candidate="candidate_b", weights=w, is_improved=True)
        ranked = rank_locations(scored)
        top1 = ranked.iloc[0]
        assert exp_dong in top1["adm_nm"], f"[{ind}+{tgt}] 1위 동 불일치: {top1['adm_nm']} != {exp_dong}"
        assert abs(top1["total_score"] - exp_sc) < 0.05, f"[{ind}+{tgt}] 점수 불일치: {top1['total_score']} != {exp_sc}"
    print("[PASS] Test 6: 6대 데모 시나리오 Candidate B 1위 및 점수 일치성 검증 통과")

    # Test 7: UI 및 설명 텍스트 내 금지어 완전 배제 검증
    forbidden_terms = ["실제 유동인구", "방문객 수", "고객 수", "소비자 수", "10개 행정동 fallback"]
    for bad in forbidden_terms:
        assert bad not in app_code, f"app.py 내 금지어 검출: {bad}"

    # 전수 150개 행정동 설명 텍스트 검증
    f_sample, m_sample = build_dong_industry_features("카페", "2030", df_dong, df_store)
    for col in bus_cols:
        f_sample[col] = df_dong[col].values
    scored_sample = calculate_enhanced_scores(f_sample, candidate="candidate_b", is_improved=True)
    ranked_sample = rank_locations(scored_sample)
    for _, row in ranked_sample.iterrows():
        exp = generate_enhanced_explanation(row, m_sample)
        full_text = exp["summary_sentence"] + " " + " ".join(exp["strengths"]) + " " + " ".join(exp["cautions"])
        for bad in forbidden_terms:
            assert bad not in full_text, f"설명 텍스트 내 금지어 검출: {bad}"
    print("[PASS] Test 7: app.py 및 150개 행정동 설명 텍스트 내 금지어 5종 완전 배제 통과")

    # Test 8: 150개 행정동 분석 데이터 CSV 내보내기 무결성 검증
    csv_cols = [
        "rank", "adm_nm", "total_score", "demand_score", "target_fit_score",
        "competition_score", "accessibility_score", "subway_accessibility_score",
        "bus_accessibility_score", "parking_score", "industry_fit_score",
        "cat_store_count", "dong_bus_stop_count", "avg_dist_to_bus_m"
    ]
    df_export = ranked_sample[csv_cols].copy()
    assert len(df_export) == 150, f"CSV 행 수 불일치: {len(df_export)}"
    assert df_export.isna().sum().sum() == 0, "CSV 내 결측치 존재"
    # UTF-8-SIG 인코딩 테스트
    csv_bytes = df_export.to_csv(index=False).encode("utf-8-sig")
    assert csv_bytes[:3] == b'\xef\xbb\xbf', "UTF-8-SIG BOM 누락"
    assert len(csv_bytes.decode("utf-8-sig").strip().split("\n")) == 151, "151줄(헤더1+데이터150) 불일치"
    print("[PASS] Test 8: 150개 행정동 CSV 내보내기 무결성(151라인, UTF-8-SIG, 결측치 0) 통과")

    # Test 9: Tab 3 모델 정량 비교 동적 스피어만 상관계수 및 현재 조건 안내 검증
    assert "spearmanr(df_compare[\"rank_base\"], df_compare[\"rank_cand\"])" in app_code
    assert "현재 선택된 업종·타깃·가중치 조건에서 실시간 산출" in app_code
    assert "Phase 8 전 업종 종합 평균" not in app_code
    print("[PASS] Test 9: Tab 3 실시간 스피어만 상관계수 계산 및 현재 조건 안내 검증 통과")

    # Test 10: 150개 행정동 전수 순위(1~150위) 및 점수(0~100) 유효성 무결성 검증
    for cand in ["baseline", "candidate_b"]:
        s = calculate_enhanced_scores(f_sample, candidate=cand, is_improved=True)
        r = rank_locations(s)
        ranks = sorted(r["rank"].tolist())
        assert ranks == list(range(1, 151)), f"{cand} 순위 연속성 위반"
        assert (r["total_score"] >= 0.0).all() and (r["total_score"] <= 100.0).all()
        assert (r["accessibility_score"] >= 0.0).all() and (r["accessibility_score"] <= 100.0).all()
    print("[PASS] Test 10: 150개 행정동 전수 순위(1~150위) 및 점수 [0, 100] 무결성 통과")

    print("=" * 70)
    print("ALL 10 PHASE 10 AUTOMATED TESTS PASSED! (100%)")
    print("=" * 70)
    return True

if __name__ == "__main__":
    success = run_phase10_tests()
    if not success:
        sys.exit(1)
