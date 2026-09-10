#!/usr/bin/env python3
"""
대구 행정동 경계 GeoJSON 수집 및 정제 스크립트
출처: 통계청(SGIS) 기반 대한민국 행정동 경계 오픈데이터 (admdongkor)
저장 위치: data/processed/geojson/대구_행정동_경계_20230701.geojson
"""

import os
import json
import requests
from pathlib import Path

GEOJSON_URL = "https://raw.githubusercontent.com/vuski/admdongkor/master/ver20230701/HangJeongDong_ver20230701.geojson"
ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_PATH = ROOT_DIR / "data/processed/geojson/대구_행정동_경계_20230701.geojson"

def collect_daegu_boundaries():
    print("=== [PHASE 4] 대구 행정동 경계 GeoJSON 수집 ===")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"1. 원격 저장소에서 행정동 경계 다운로드 중...\n   URL: {GEOJSON_URL}")
    r = requests.get(GEOJSON_URL, timeout=30)
    r.raise_for_status()
    data = r.json()
    
    features = data.get("features", [])
    print(f"2. 전국 행정동 피처 수: {len(features):,}개")
    
    # 대구광역시 필터링 (sido == '27' 또는 sidonm == '대구광역시')
    daegu_features = [
        f for f in features
        if f["properties"].get("sido") == "27" or f["properties"].get("sidonm") == "대구광역시"
    ]
    
    daegu_geojson = {
        "type": "FeatureCollection",
        "name": "daegu_hangjeongdong_boundaries",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}
        },
        "features": daegu_features
    }
    
    print(f"3. 대구광역시 추출 행정동 피처 수: {len(daegu_features):,}개")
    
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(daegu_geojson, f, ensure_ascii=False, indent=2)
        
    file_size = os.path.getsize(OUTPUT_PATH)
    print(f"4. 저장 완료: {OUTPUT_PATH}")
    print(f"   파일 크기: {file_size:,} bytes ({file_size / (1024*1024):.2f} MB)")
    print("=== 행정동 경계 수집 완료 ===")

if __name__ == "__main__":
    collect_daegu_boundaries()
