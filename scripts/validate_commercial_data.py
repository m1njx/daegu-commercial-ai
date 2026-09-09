#!/usr/bin/env python3
"""
대구 소상공인 상가(상권)정보 원본 데이터 종합 품질 검증 스크립트
"""

import os
import sys
import json
from pathlib import Path
import pandas as pd
import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT_DIR / "data/raw/commercial/소상공인시장진흥공단_상가상권정보/소상공인시장진흥공단_상가업소정보_대구_20260907.csv"

def run_validation():
    if not os.path.exists(CSV_PATH):
        print(f"[ERROR] 파일이 존재하지 않습니다: {CSV_PATH}", file=sys.stderr)
        sys.exit(1)
        
    print("=== [PHASE 3] 대구 상가업소정보 데이터 종합 품질 검증 ===")
    file_size = os.path.getsize(CSV_PATH)
    print(f"1. 파일 경로: {CSV_PATH}")
    print(f"   파일 크기: {file_size:,} bytes ({file_size / (1024*1024):.2f} MB)")
    
    # 1. 데이터 로드
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig", low_memory=False)
    rows, cols = df.shape
    print(f"   데이터 형태: {rows:,}행 × {cols}열")
    
    # 2. 중복 검증
    full_duplicates = df.duplicated().sum()
    id_duplicates = df["bizesId"].duplicated().sum() if "bizesId" in df.columns else None
    print(f"\n2. 중복 검증:")
    print(f"   - 완전 중복 행: {full_duplicates}건")
    print(f"   - 상가업소번호(bizesId) 중복 건수: {id_duplicates}건")
    
    # 3. 결측률 분석
    print(f"\n3. 주요 컬럼 결측치 분석:")
    key_cols = [
        "bizesId", "bizesNm", "brchNm", "indsLclsCd", "indsLclsNm",
        "indsMclsCd", "indsMclsNm", "indsSclsCd", "indsSclsNm",
        "ksicCd", "ksicNm", "ctprvnCd", "ctprvnNm", "signguCd", "signguNm",
        "adongCd", "adongNm", "ldongCd", "ldongNm", "rdnmAdr", "lnoAdr",
        "lon", "lat"
    ]
    missing_summary = {}
    for c in key_cols:
        if c in df.columns:
            null_cnt = int(df[c].isnull().sum())
            null_pct = round((null_cnt / rows) * 100, 2)
            missing_summary[c] = {"null_count": null_cnt, "null_pct": null_pct}
            print(f"   - {c:12s}: {null_cnt:,}건 ({null_pct}%)")
            
    # 4. 지역 검증 (대구 한정 여부)
    print(f"\n4. 지역 검증:")
    sido_counts = df["ctprvnNm"].value_counts(dropna=False).to_dict()
    print(f"   - 시도명 분포: {sido_counts}")
    is_pure_daegu = (list(sido_counts.keys()) == ["대구광역시"])
    print(f"   - 100% 대구광역시 데이터 여부: {'PASS' if is_pure_daegu else 'FAIL'}")
    
    sigungu_counts = df["signguNm"].value_counts(dropna=False).to_dict()
    print(f"   - 시군구 분포 ({len(sigungu_counts)}개 구·군):")
    for sgg, cnt in sigungu_counts.items():
        print(f"     * {sgg}: {cnt:,}건 ({cnt/rows*100:.1f}%)")
        
    adong_unique = df["adongNm"].nunique()
    print(f"   - 고유 행정동 수: {adong_unique}개")
    
    # 5. 좌표 검증
    print(f"\n5. 좌표 검증 (경도: lon, 위도: lat):")
    df["lon_num"] = pd.to_numeric(df["lon"], errors="coerce")
    df["lat_num"] = pd.to_numeric(df["lat"], errors="coerce")
    
    lon_null = int(df["lon_num"].isnull().sum())
    lat_null = int(df["lat_num"].isnull().sum())
    print(f"   - 경도 결측/변환실패: {lon_null}건")
    print(f"   - 위도 결측/변환실패: {lat_null}건")
    
    # 대구 BBox: 128.30 ~ 128.85 E, 35.55 ~ 36.10 N (군위군 포함)
    valid_coords = df.dropna(subset=["lon_num", "lat_num"])
    out_of_bounds = valid_coords[
        (valid_coords["lon_num"] < 128.30) | (valid_coords["lon_num"] > 128.85) |
        (valid_coords["lat_num"] < 35.55) | (valid_coords["lat_num"] > 36.30)
    ]
    print(f"   - 경도 범위: {valid_coords['lon_num'].min():.6f} ~ {valid_coords['lon_num'].max():.6f}")
    print(f"   - 위도 범위: {valid_coords['lat_num'].min():.6f} ~ {valid_coords['lat_num'].max():.6f}")
    print(f"   - 대구 영역 이탈 좌표 수: {len(out_of_bounds)}건")
    
    # 6. 업종 분포 분석
    print(f"\n6. 업종 분포 분석:")
    lcls_counts = df["indsLclsNm"].value_counts().to_dict()
    print(f"   - 업종 대분류 ({len(lcls_counts)}개):")
    for lcls, cnt in lcls_counts.items():
        print(f"     * {lcls}: {cnt:,}건 ({cnt/rows*100:.1f}%)")
        
    mcls_counts = df["indsMclsNm"].value_counts().head(10).to_dict()
    print(f"   - 업종 중분류 Top 10:")
    for mcls, cnt in mcls_counts.items():
        print(f"     * {mcls}: {cnt:,}건 ({cnt/rows*100:.1f}%)")
        
    scls_counts = df["indsSclsNm"].value_counts().head(20).to_dict()
    print(f"   - 업종 소분류 Top 20:")
    for scls, cnt in scls_counts.items():
        print(f"     * {scls}: {cnt:,}건 ({cnt/rows*100:.1f}%)")
        
    # 결과 JSON 저장
    result_data = {
        "file_size": file_size,
        "rows": rows,
        "cols": cols,
        "columns": df.columns.drop(["lon_num", "lat_num"]).tolist(),
        "full_duplicates": int(full_duplicates),
        "id_duplicates": int(id_duplicates) if id_duplicates is not None else 0,
        "missing_summary": missing_summary,
        "is_pure_daegu": is_pure_daegu,
        "sigungu_counts": sigungu_counts,
        "adong_unique_count": int(adong_unique),
        "coords_stats": {
            "lon_min": float(valid_coords["lon_num"].min()),
            "lon_max": float(valid_coords["lon_num"].max()),
            "lat_min": float(valid_coords["lat_num"].min()),
            "lat_max": float(valid_coords["lat_num"].max()),
            "out_of_bounds_count": len(out_of_bounds)
        },
        "industry_lcls": lcls_counts,
        "industry_mcls_top10": mcls_counts,
        "industry_scls_top20": scls_counts
    }
    
    report_json_path = ROOT_DIR / "reports/phase3_validation_result.json"
    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    print(f"\n검증 결과 JSON 저장 완료: {report_json_path}")
    print("=== 검증 완료 ===")

if __name__ == "__main__":
    run_validation()
