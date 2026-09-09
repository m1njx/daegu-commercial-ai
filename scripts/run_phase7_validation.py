# -*- coding: utf-8 -*-
"""
scripts/run_phase7_validation.py

Phase 7 출품용 서비스 종합 자동화 검증 스위트 (12대 테스트 전수 검증)
- Test 1: UI import 및 구문 유효성 검사 (py_compile & 컴포넌트 검사)
- Test 2: 실시간 추천 실행 테스트 (Improved model recommend() 정상 반환)
- Test 3: 94개 도시철도역 Folium 마커 안전 생성 및 HTML 렌더링 테스트
- Test 4: 150개 행정동 결과 완전성 테스트
- Test 5: 94개 도시철도역 좌표 유효성 테스트 (위경도 범위 및 결측치 0)
- Test 6: 결측치(NaN/Inf) 0건 검증
- Test 7: 점수 범위 [0, 100] 검증
- Test 8: 순위 유일성 및 연속성 [1..150] 검증
- Test 9: 개인화 가중치 극단값 및 정규화 무결성 테스트
- Test 10: 0점포 보정 및 감점 계수 alpha=0.50 민감도 검증 (숙박 23개 동)
- Test 11: 유효하지 않은 입력값(Invalid Input) 예외 방어 테스트
- Test 12: 6대 데모 시나리오 실시간 재현성 및 phase7_demo_results.json 일치 검증
"""

import sys
import os
import json
import time
import py_compile
from pathlib import Path
import numpy as np
import pandas as pd
import folium

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.recommendation.feature_builder import build_dong_industry_features
from src.recommendation.scoring import calculate_component_scores, compute_total_score, BASELINE_WEIGHTS
from src.recommendation.ranking import rank_locations
from src.recommendation.explain import generate_explanation
from src.recommendation.improved import calculate_improved_scores, generate_improved_explanation
from src.recommendation.personalization import (
    validate_and_normalize_weights,
    WEIGHT_PRESETS,
    is_baseline_weights,
    format_weights_summary
)

def run_phase7_validation():
    print("==================================================")
    print("PHASE 7: 12대 자동화 종합 검증 스위트 실행")
    print("==================================================")
    
    start_all = time.time()
    test_results = []
    
    # ----------------------------------------------------
    # 데이터셋 로딩
    # ----------------------------------------------------
    t0 = time.time()
    dong_path = ROOT_DIR / "data/processed/feature_mart/commercial_feature_mart_dong.parquet"
    store_path = ROOT_DIR / "data/processed/feature_mart/store_spatial_features.parquet"
    station_path = ROOT_DIR / "data/processed/transit/대구도시철도_역별_위경도좌표.csv"
    demo_json_path = ROOT_DIR / "reports/phase7_demo_results.json"
    app_path = ROOT_DIR / "app/app.py"
    
    assert dong_path.exists(), f"파일 누락: {dong_path}"
    assert store_path.exists(), f"파일 누락: {store_path}"
    assert station_path.exists(), f"파일 누락: {station_path}"
    assert demo_json_path.exists(), f"파일 누락: {demo_json_path}"
    assert app_path.exists(), f"파일 누락: {app_path}"
    
    df_dong = pd.read_parquet(dong_path)
    df_store = pd.read_parquet(store_path)
    df_station = pd.read_csv(station_path)
    with open(demo_json_path, "r", encoding="utf-8") as f:
        demo_data = json.load(f)
    t_load = time.time() - t0
    print(f"[*] 데이터 로딩 완료: {t_load:.3f}초 (행정동 {len(df_dong)}개, 점포 {len(df_store):,}개, 역 {len(df_station)}개)")

    # ----------------------------------------------------
    # Test 1: UI import 및 구문 유효성 검사
    # ----------------------------------------------------
    print("\n[실행] Test 1: UI import 및 구문 유효성 검사 (app/app.py)")
    try:
        py_compile.compile(str(app_path), doraise=True)
        with open(app_path, "r", encoding="utf-8") as f:
            app_code = f.read()
        assert "DEMO_SCENARIOS" in app_code, "DEMO_SCENARIOS 상수 누락"
        assert "folium.Map" in app_code, "folium.Map 객체 생성 코드 누락"
        assert "folium.Choropleth" in app_code, "folium.Choropleth 시각화 코드 누락"
        assert "iM뱅크" in app_code, "iM뱅크 금융 연계 로드맵 섹션 누락"
        print("  -> PASS: app/app.py 바이트코드 컴파일 완료 및 핵심 UI 컴포넌트 구문 검증 성공")
        test_results.append(("Test 1: UI import 및 구문 유효성 검사", "PASS", "컴파일 정상, 핵심 컴포넌트 확인"))
    except Exception as e:
        print(f"  -> FAIL: {e}")
        test_results.append(("Test 1: UI import 및 구문 유효성 검사", "FAIL", str(e)))

    # ----------------------------------------------------
    # Test 2: 실시간 추천 실행 테스트
    # ----------------------------------------------------
    print("\n[실행] Test 2: 실시간 추천 엔진 실행 테스트 (Improved model)")
    try:
        t_rec0 = time.time()
        feat, meta = build_dong_industry_features("카페", "2030", df_dong, df_store)
        scored = calculate_improved_scores(feat, min_stores=1, discount_factor=0.50)
        ranked = rank_locations(scored)
        t_rec = time.time() - t_rec0
        assert isinstance(ranked, pd.DataFrame), "반환 타입이 DataFrame이 아님"
        assert len(ranked) == 150, f"반환 행 수가 150이 아님: {len(ranked)}"
        assert "total_score" in ranked.columns, "total_score 컬럼 누락"
        assert "market_status" in ranked.columns, "market_status 컬럼 누락"
        exp = generate_improved_explanation(ranked.iloc[0], meta)
        assert "summary_sentence" in exp, "설명 요약 문장 누락"
        print(f"  -> PASS: 실시간 추천 실행 소요시간 {t_rec:.3f}초, 150개 동 랭킹 및 설명 정상 산출")
        test_results.append(("Test 2: 실시간 추천 실행 테스트", "PASS", f"소요시간 {t_rec:.3f}초"))
    except Exception as e:
        print(f"  -> FAIL: {e}")
        test_results.append(("Test 2: 실시간 추천 실행 테스트", "FAIL", str(e)))

    # ----------------------------------------------------
    # Test 3: 94개 도시철도역 Folium 마커 안전 생성 및 HTML 렌더링 테스트
    # ----------------------------------------------------
    print("\n[실행] Test 3: 94개 도시철도역 Folium 마커 안전 생성 및 HTML 렌더링 테스트")
    try:
        t_map0 = time.time()
        m = folium.Map(location=[35.8714, 128.6014], zoom_start=12)
        station_grp = folium.FeatureGroup(name="도시철도역 (94개소)")
        
        station_cols = df_station.columns.tolist()
        lat_col = "lat" if "lat" in station_cols else [c for c in station_cols if "위도" in c or "lat" in c.lower()][0]
        lon_col = "lon" if "lon" in station_cols else [c for c in station_cols if "경도" in c or "lon" in c.lower()][0]
        name_col = "역명" if "역명" in station_cols else [c for c in station_cols if "역" in c or "name" in c.lower()][0]
        
        marker_count = 0
        for _, st in df_station.iterrows():
            st_lat = float(st[lat_col])
            st_lon = float(st[lon_col])
            st_name = str(st[name_col])
            folium.CircleMarker(
                location=[st_lat, st_lon],
                radius=3.5,
                color="#1A237E",
                fill=True,
                fill_color="#3949AB",
                fill_opacity=0.85,
                popup=st_name,
                tooltip=st_name
            ).add_to(station_grp)
            marker_count += 1
            
        station_grp.add_to(m)
        html_str = m.get_root().render()
        t_map = time.time() - t_map0
        assert marker_count == 94, f"마커 개수 불일치: {marker_count} != 94"
        assert len(html_str) > 1000, "생성된 HTML 문자열이 비정상적으로 짧음"
        print(f"  -> PASS: 94개 도시철도역 마커 생성 및 Folium HTML 렌더링 성공 (소요시간 {t_map:.3f}초, HTML 길이 {len(html_str):,}B)")
        test_results.append(("Test 3: 94개 도시철도역 Folium 마커 안전 생성", "PASS", f"94개 마커, {t_map:.3f}초"))
    except Exception as e:
        print(f"  -> FAIL: {e}")
        test_results.append(("Test 3: 94개 도시철도역 Folium 마커 안전 생성", "FAIL", str(e)))

    # ----------------------------------------------------
    # Test 4: 150개 행정동 완전성 테스트
    # ----------------------------------------------------
    print("\n[실행] Test 4: 150개 행정동 완전성 테스트")
    try:
        assert len(df_dong) == 150, f"Feature Mart 행정동 수 오류: {len(df_dong)}"
        assert df_dong["adm_cd2"].nunique() == 150, "adm_cd2 중복 또는 누락"
        assert df_dong["adm_nm"].nunique() == 150, "adm_nm 중복 또는 누락"
        assert df_dong["adm_cd2"].isna().sum() == 0, "adm_cd2 결측치 존재"
        assert df_dong["adm_nm"].isna().sum() == 0, "adm_nm 결측치 존재"
        print("  -> PASS: 150개 행정동 고유 코드 및 명칭 100% 완전성 확인 (결측치 0건)")
        test_results.append(("Test 4: 150개 행정동 완전성 테스트", "PASS", "150개 동 고유코드/명칭 결측치 0"))
    except Exception as e:
        print(f"  -> FAIL: {e}")
        test_results.append(("Test 4: 150개 행정동 완전성 테스트", "FAIL", str(e)))

    # ----------------------------------------------------
    # Test 5: 94개 도시철도역 좌표 유효성 테스트
    # ----------------------------------------------------
    print("\n[실행] Test 5: 94개 도시철도역 좌표 유효성 테스트")
    try:
        assert len(df_station) == 94, f"도시철도역 수 불일치: {len(df_station)}"
        lat_vals = df_station[lat_col].astype(float)
        lon_vals = df_station[lon_col].astype(float)
        assert lat_vals.isna().sum() == 0, "위도 결측치 발견"
        assert lon_vals.isna().sum() == 0, "경도 결측치 발견"
        # 대구 도시철도 1/2/3호선 실제 운행 구간: 위도 35.75~36.00, 경도 128.40~128.85 (하양/경산 연장선 포함)
        assert (lat_vals >= 35.75).all() and (lat_vals <= 36.00).all(), f"위도 범위 이탈: min={lat_vals.min()}, max={lat_vals.max()}"
        assert (lon_vals >= 128.40).all() and (lon_vals <= 128.85).all(), f"경도 범위 이탈: min={lon_vals.min()}, max={lon_vals.max()}"
        print(f"  -> PASS: 94개 역 좌표 유효성 확인 (위도 {lat_vals.min():.4f}~{lat_vals.max():.4f}, 경도 {lon_vals.min():.4f}~{lon_vals.max():.4f}, 결측치 0)")
        test_results.append(("Test 5: 94개 도시철도역 좌표 유효성 테스트", "PASS", "위경도 대구 도시철도 관내 유효범위, 결측치 0"))
    except Exception as e:
        print(f"  -> FAIL: {e}")
        test_results.append(("Test 5: 94개 도시철도역 좌표 유효성 테스트", "FAIL", str(e)))

    # ----------------------------------------------------
    # Test 6: 결측치(NaN/Inf) 0건 검증
    # ----------------------------------------------------
    print("\n[실행] Test 6: 결측치(NaN/Inf) 0건 검증")
    try:
        feat_chk, _ = build_dong_industry_features("한식", "전체", df_dong, df_store)
        scored_chk = calculate_improved_scores(feat_chk)
        score_cols = ["total_score", "demand_score", "target_fit_score", "competition_score", "accessibility_score", "parking_score", "industry_fit_score"]
        nan_total = 0
        inf_total = 0
        for sc in score_cols:
            nan_cnt = scored_chk[sc].isna().sum()
            inf_cnt = np.isinf(scored_chk[sc]).sum()
            nan_total += nan_cnt
            inf_total += inf_cnt
        assert nan_total == 0, f"NaN 발견: {nan_total}건"
        assert inf_total == 0, f"Inf 발견: {inf_total}건"
        print("  -> PASS: 7대 점수 컬럼(종합 및 6대 컴포넌트) 150개 동 전수 NaN/Inf 0건 확인")
        test_results.append(("Test 6: 결측치(NaN/Inf) 0건 검증", "PASS", "7개 점수 컬럼 전수 NaN=0, Inf=0"))
    except Exception as e:
        print(f"  -> FAIL: {e}")
        test_results.append(("Test 6: 결측치(NaN/Inf) 0건 검증", "FAIL", str(e)))

    # ----------------------------------------------------
    # Test 7: 점수 범위 [0, 100] 검증
    # ----------------------------------------------------
    print("\n[실행] Test 7: 점수 범위 [0, 100] 검증")
    try:
        min_val = scored_chk["total_score"].min()
        max_val = scored_chk["total_score"].max()
        assert 0.0 <= min_val <= 100.0, f"최소 점수 범위 이탈: {min_val}"
        assert 0.0 <= max_val <= 100.0, f"최대 점수 범위 이탈: {max_val}"
        for sc in score_cols[1:]:
            c_min = scored_chk[sc].min()
            c_max = scored_chk[sc].max()
            assert 0.0 <= c_min <= 100.0, f"{sc} 최소점수 이탈: {c_min}"
            assert 0.0 <= c_max <= 100.0, f"{sc} 최대점수 이탈: {c_max}"
        print(f"  -> PASS: 종합 점수({min_val:.2f}~{max_val:.2f}) 및 6대 컴포넌트 점수 전수 [0.0, 100.0] 범위 충족")
        test_results.append(("Test 7: 점수 범위 [0, 100] 검증", "PASS", f"최소 {min_val:.2f}, 최대 {max_val:.2f} (전부 [0, 100])"))
    except Exception as e:
        print(f"  -> FAIL: {e}")
        test_results.append(("Test 7: 점수 범위 [0, 100] 검증", "FAIL", str(e)))

    # ----------------------------------------------------
    # Test 8: 순위 유일성 및 연속성 [1..150] 검증
    # ----------------------------------------------------
    print("\n[실행] Test 8: 순위 유일성 및 연속성 [1..150] 검증")
    try:
        ranked_chk = rank_locations(scored_chk)
        ranks = list(ranked_chk["rank"].values)
        assert ranks == list(range(1, 151)), "순위가 1부터 150까지 연속적이지 않거나 중복/동점 존재"
        assert len(set(ranks)) == 150, "순위 중복 발견"
        print("  -> PASS: 150개 행정동 1위부터 150위까지 완벽한 고유성 및 연속성 검증 성공")
        test_results.append(("Test 8: 순위 유일성 및 연속성 [1..150] 검증", "PASS", "1..150 중복 없는 완전 순위 확인"))
    except Exception as e:
        print(f"  -> FAIL: {e}")
        test_results.append(("Test 8: 순위 유일성 및 연속성 [1..150] 검증", "FAIL", str(e)))

    # ----------------------------------------------------
    # Test 9: 개인화 가중치 극단값 및 정규화 무결성 테스트
    # ----------------------------------------------------
    print("\n[실행] Test 9: 개인화 가중치 극단값 및 정규화 무결성 테스트")
    try:
        single_w = {"demand": 1.0, "target_fit": 0.0, "competition": 0.0, "accessibility": 0.0, "parking": 0.0, "industry_fit": 0.0}
        norm_sw = validate_and_normalize_weights(single_w)
        s_sw = calculate_improved_scores(feat_chk, weights=norm_sw)
        diff = (s_sw["total_score"] - s_sw["demand_score"]).abs().max()
        assert diff <= 0.02, f"단일 가중치 일치 실패: diff={diff}"
        
        all_zero = {k: 0.0 for k in BASELINE_WEIGHTS.keys()}
        norm_zero = validate_and_normalize_weights(all_zero)
        assert is_baseline_weights(norm_zero), "전부 0일 때 Baseline 복원 실패"
        
        neg_w = {"demand": -100.0, "target_fit": 50.0, "competition": 50.0, "accessibility": 0.0, "parking": 0.0, "industry_fit": 0.0}
        norm_neg = validate_and_normalize_weights(neg_w)
        assert norm_neg["demand"] == 0.0, "음수 가중치 클리핑 실패"
        assert abs(sum(norm_neg.values()) - 1.0) < 1e-4, "음수 정규화 합계 1.0 오류"
        
        print("  -> PASS: 100% 단일 가중치, 전 가중치 0 Fallback, 음수 방어 및 합계 1.0 정규화 정상 동작 확인")
        test_results.append(("Test 9: 개인화 가중치 극단값 및 정규화 무결성", "PASS", "단일 100%, 0 Fallback, 음수 클리핑 전부 통과"))
    except Exception as e:
        print(f"  -> FAIL: {e}")
        test_results.append(("Test 9: 개인화 가중치 극단값 및 정규화 무결성", "FAIL", str(e)))

    # ----------------------------------------------------
    # Test 10: 0점포 보정 및 감점 계수 alpha=0.50 민감도 검증 (숙박 23개 동)
    # ----------------------------------------------------
    print("\n[실행] Test 10: 0점포 보정 및 감점 계수 alpha=0.50 민감도 검증 (숙박 23개 동)")
    try:
        feat_l, meta_l = build_dong_industry_features("숙박", "2030", df_dong, df_store)
        zero_cnt = (feat_l["cat_store_count"] == 0).sum()
        assert zero_cnt == 23, f"숙박 0개 점포 동 수 불일치: {zero_cnt} != 23"
        
        base_l = rank_locations(compute_total_score(calculate_component_scores(feat_l.copy())))
        imp_l = rank_locations(calculate_improved_scores(feat_l.copy(), min_stores=1, discount_factor=0.50))
        
        yongsan_base = base_l[base_l["adm_nm"] == "대구광역시 달서구 용산1동"].iloc[0]
        yongsan_imp = imp_l[imp_l["adm_nm"] == "대구광역시 달서구 용산1동"].iloc[0]
        
        assert yongsan_base["rank"] == 3, f"Baseline 용산1동 순위 오류: {yongsan_base['rank']}"
        assert yongsan_imp["rank"] == 15, f"Improved 용산1동 보정 순위 불일치: {yongsan_imp['rank']} != 15"
        assert yongsan_imp["market_status"] == "미진입 상권 (점포 0개)", f"라벨 오류: {yongsan_imp['market_status']}"
        assert yongsan_imp["competition_score"] == round(yongsan_base["competition_score"] * 0.50, 2), "alpha=0.50 정확한 할인율 미적용"
        
        print(f"  -> PASS: 0점포 23개 동 식별, 용산1동 3위 -> 15위 보정(alpha=0.50 경쟁점수 50% 할인) 정상 검증")
        test_results.append(("Test 10: 0점포 보정 및 alpha=0.50 민감도 검증", "PASS", f"용산1동 3위->{yongsan_imp['rank']}위, 23개 0점포 식별"))
    except Exception as e:
        print(f"  -> FAIL: {e}")
        test_results.append(("Test 10: 0점포 보정 및 alpha=0.50 민감도 검증", "FAIL", str(e)))

    # ----------------------------------------------------
    # Test 11: 유효하지 않은 입력값(Invalid Input) 예외 방어 테스트
    # ----------------------------------------------------
    print("\n[실행] Test 11: 유효하지 않은 입력값(Invalid Input) 예외 방어 테스트")
    try:
        val_err_caught = False
        try:
            build_dong_industry_features("초전도체제조업", "2030", df_dong, df_store)
        except ValueError:
            val_err_caught = True
        assert val_err_caught, "미지원 업종에 대해 ValueError가 발생하지 않음"
        
        _, meta_fall = build_dong_industry_features("카페", "외계인타깃", df_dong, df_store)
        assert "2030" in meta_fall["target_demographic_label"], "알 수 없는 연령층 기본 Fallback 실패"
        
        print("  -> PASS: 미지원 업종 ValueError 안전 차단 및 알 수 없는 연령 Fallback 방어 확인")
        test_results.append(("Test 11: 유효하지 않은 입력값 예외 방어", "PASS", "미지원 업종 ValueError 차단, 타깃 Fallback 정상"))
    except Exception as e:
        print(f"  -> FAIL: {e}")
        test_results.append(("Test 11: 유효하지 않은 입력값 예외 방어", "FAIL", str(e)))

    # ----------------------------------------------------
    # Test 12: 6대 데모 시나리오 실시간 재현성 및 phase7_demo_results.json 일치 검증
    # ----------------------------------------------------
    print("\n[실행] Test 12: 6대 데모 시나리오 실시간 재현성 및 phase7_demo_results.json 일치 검증")
    try:
        for scen_key, scen_val in demo_data.items():
            ind = scen_val["industry"]
            tgt = scen_val["target"]
            expected_top5 = scen_val["top5_improved"]
            
            feat_live, _ = build_dong_industry_features(ind, tgt, df_dong, df_store)
            scored_live = calculate_improved_scores(feat_live, min_stores=1, discount_factor=0.50)
            ranked_live = rank_locations(scored_live)
            live_top5 = ranked_live.head(5)
            
            for i in range(5):
                exp_row = expected_top5[i]
                live_row = live_top5.iloc[i]
                
                assert exp_row["adm_nm"] == live_row["adm_nm"], f"[{scen_key}] {i+1}위 동 불일치: {exp_row['adm_nm']} != {live_row['adm_nm']}"
                diff_score = abs(exp_row["total_score"] - live_row["total_score"])
                assert diff_score <= 0.01, f"[{scen_key}] {i+1}위 점수 불일치: {exp_row['total_score']} != {live_row['total_score']}"
                
            print(f"    - '{scen_key}': Top 5 실시간 재현 일치 (1위 {live_top5.iloc[0]['adm_nm']} {live_top5.iloc[0]['total_score']}점)")
            
        print("  -> PASS: 6대 실전 데모 시나리오 Top 1~5 행정동 및 점수 전수 100% 일치 확인")
        test_results.append(("Test 12: 6대 데모 시나리오 실시간 재현성 일치", "PASS", "6개 시나리오 Top 5 전수 100% 일치"))
    except Exception as e:
        print(f"  -> FAIL: {e}")
        test_results.append(("Test 12: 6대 데모 시나리오 실시간 재현성 일치", "FAIL", str(e)))

    # ----------------------------------------------------
    # 최종 결과 요약
    # ----------------------------------------------------
    t_total = time.time() - start_all
    print("\n==================================================")
    print(f"PHASE 7: 12대 자동화 테스트 종합 결과 (총 소요시간: {t_total:.2f}초)")
    print("==================================================")
    all_pass = True
    for name, status, detail in test_results:
        print(f"  [{status}] {name} - {detail}")
        if status != "PASS":
            all_pass = False
            
    print(f"\n최종 판정: {'ALL 12 TESTS PASSED (100%)' if all_pass else 'SOME TESTS FAILED'}")
    return all_pass, test_results

if __name__ == "__main__":
    success, _ = run_phase7_validation()
    if not success:
        sys.exit(1)
