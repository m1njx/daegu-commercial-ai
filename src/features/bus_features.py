# -*- coding: utf-8 -*-
"""
src/features/bus_features.py

대구 시내버스 정류소 위치 및 월별 승하차 데이터 통합 가공 모듈
- 150개 행정동 공간 결합 (EPSG:5179 UTM-K 투영)
- 2026년 1월 ~ 7월 (212일간) 정류소별 일평균 승하차 산출
- 행정동 단위 및 점포 단위 대중교통(버스) 피처 엔지니어링
- 원본 raw 데이터 무수정 보존 및 processed 저장
"""

import os

import unicodedata
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import pyproj
from scipy.spatial import cKDTree

# 기본 경로 설정
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_BUS_DIR = DATA_DIR / "raw" / "bus"
PROCESSED_BUS_DIR = DATA_DIR / "processed" / "transit" / "bus"
GEOJSON_PATH = DATA_DIR / "processed" / "geojson" / "대구_행정동_경계_20230701.geojson"
DONG_MART_PATH = DATA_DIR / "processed" / "feature_mart" / "commercial_feature_mart_dong.parquet"
STORE_MART_PATH = DATA_DIR / "processed" / "feature_mart" / "store_spatial_features.parquet"

# 2026년 1월 ~ 7월 총 일수 (31+28+31+30+31+30+31)
TOTAL_PERIOD_DAYS_2026: int = 212

def find_bus_raw_files() -> Tuple[Path, Path]:
    """
    NFC/NFD 및 공백 차이에 관계없이 실제 filesystem entry에서 버스 원천 파일을 탐색합니다.
    """
    loc_file = None
    rid_file = None
    
    # 1. 위치정보 파일 탐색
    for item in RAW_BUS_DIR.iterdir():
        normalized_name = unicodedata.normalize("NFC", item.name)
        if "정류소" in normalized_name and "위치" in normalized_name and item.suffix.lower() == ".csv":
            loc_file = item
            break
            
    # 2. 이용자수 파일 탐색
    for item in RAW_BUS_DIR.iterdir():
        normalized_name = unicodedata.normalize("NFC", item.name)
        if item.is_dir() and "정류소별" in normalized_name and "이용자수" in normalized_name:
            for sub in item.iterdir():
                sub_norm = unicodedata.normalize("NFC", sub.name)
                if "2026" in sub_norm and sub.suffix.lower() == ".csv":
                    rid_file = sub
                    break
                    
    if loc_file is None or not loc_file.exists():
        raise FileNotFoundError(f"버스 정류소 위치정보 CSV를 찾을 수 없습니다: {RAW_BUS_DIR}")
    if rid_file is None or not rid_file.exists():
        raise FileNotFoundError(f"버스 정류소 이용자수(2026) CSV를 찾을 수 없습니다: {RAW_BUS_DIR}")
        
    return loc_file, rid_file

def load_and_clean_bus_data() -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    원천 버스 위치 및 이용자수 데이터를 로드하고 유효성을 검사합니다.
    """
    loc_path, rid_path = find_bus_raw_files()
    
    # CSV 로드 (UTF-8-SIG 적용)
    df_loc = pd.read_csv(loc_path, encoding="utf-8-sig")
    df_rid = pd.read_csv(rid_path, encoding="utf-8-sig")
    
    # 컬럼 공백 제거
    df_loc.columns = [c.strip() for c in df_loc.columns]
    df_rid.columns = [c.strip() for c in df_rid.columns]
    
    # 정류소명 NFC 정규화 및 공백 정제
    df_loc["정류소명"] = df_loc["정류소명"].astype(str).apply(lambda s: unicodedata.normalize("NFC", s.strip()))
    df_rid["정류소명"] = df_rid["정류소명"].astype(str).apply(lambda s: unicodedata.normalize("NFC", s.strip()))
    
    # 조인 매칭 통계 산출
    unique_loc_names = set(df_loc["정류소명"].unique())
    unique_rid_names = set(df_rid["정류소명"].unique())
    matched_names = unique_rid_names.intersection(unique_loc_names)
    unmatched_rid_names = unique_rid_names - unique_loc_names
    unmatched_loc_names = unique_loc_names - unique_rid_names
    
    total_rid_vol = int(df_rid["합계"].sum())
    matched_rid_vol = int(df_rid[df_rid["정류소명"].isin(unique_loc_names)]["합계"].sum())
    unmatched_rid_vol = total_rid_vol - matched_rid_vol
    
    join_stats = {
        "loc_file_name": loc_path.name,
        "rid_file_name": rid_path.name,
        "loc_total_rows": len(df_loc),
        "loc_unique_stops": len(unique_loc_names),
        "rid_total_rows": len(df_rid),
        "rid_unique_stops": len(unique_rid_names),
        "matched_stop_names": len(matched_names),
        "stop_name_match_rate_pct": round(len(matched_names) / len(unique_rid_names) * 100.0, 2),
        "unmatched_rid_stops": len(unmatched_rid_names),
        "unmatched_loc_stops": len(unmatched_loc_names),
        "total_ridership_volume": total_rid_vol,
        "matched_ridership_volume": matched_rid_vol,
        "ridership_volume_coverage_pct": round(matched_rid_vol / total_rid_vol * 100.0, 2),
        "months_covered": sorted(df_rid["년월"].unique().tolist()),
        "total_days_in_period": TOTAL_PERIOD_DAYS_2026,
    }
    
    return df_loc, df_rid, join_stats

def build_bus_feature_mart(save: bool = True) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    정류소별 위치와 이용자수를 150개 행정동 및 11.8만 개 점포와 공간 결합하여
    행정동 단위 버스 Feature Mart를 생성합니다.
    """
    PROCESSED_BUS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. 데이터 로드
    df_loc, df_rid, join_stats = load_and_clean_bus_data()
    gdf_dong = gpd.read_file(GEOJSON_PATH).to_crs(epsg=5179)
    df_dong_mart = pd.read_parquet(DONG_MART_PATH)
    
    # 2. 좌표 변환 (WGS84 EPSG:4326 -> UTM-K EPSG:5179)
    transformer = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:5179", always_xy=True)
    bus_x, bus_y = transformer.transform(df_loc["경도"].values, df_loc["위도"].values)
    df_loc["x_utm"] = bus_x
    df_loc["y_utm"] = bus_y
    
    # 3. 공간 결합 (150개 행정동)
    gdf_bus = gpd.GeoDataFrame(df_loc, geometry=[Point(xy) for xy in zip(bus_x, bus_y)], crs="EPSG:5179")
    gdf_bus_joined = gpd.sjoin(gdf_bus, gdf_dong[["adm_cd2", "adm_nm", "geometry"]], how="left", predicate="within")
    
    # 경계선 인접 5개 정류소 최근접 행정동 스냅
    unmapped_mask = gdf_bus_joined["adm_cd2"].isnull()
    unmapped_idx = gdf_bus_joined[unmapped_mask].index
    for idx in unmapped_idx:
        pt = gdf_bus_joined.loc[idx, "geometry"]
        dists = gdf_dong.distance(pt)
        nearest_idx = dists.idxmin()
        gdf_bus_joined.loc[idx, "adm_cd2"] = gdf_dong.loc[nearest_idx, "adm_cd2"]
        gdf_bus_joined.loc[idx, "adm_nm"] = gdf_dong.loc[nearest_idx, "adm_nm"]
        
    # 4. 정류소별 7개월 누적 합계 및 일평균 승하차 계산
    stop_rid = df_rid.groupby("정류소명").agg({
        "승차": "sum",
        "하차": "sum",
        "합계": "sum"
    }).reset_index()
    stop_rid["daily_boarding"] = (stop_rid["승차"] / TOTAL_PERIOD_DAYS_2026).round(2)
    stop_rid["daily_alighting"] = (stop_rid["하차"] / TOTAL_PERIOD_DAYS_2026).round(2)
    stop_rid["daily_total"] = (stop_rid["합계"] / TOTAL_PERIOD_DAYS_2026).round(2)
    
    # 5. 동일 정류소명 다중 표지판(상·하행) 승하차 할당
    pole_counts = gdf_bus_joined.groupby("정류소명").size().rename("pole_count")
    gdf_bus_joined = gdf_bus_joined.merge(pole_counts, on="정류소명", how="left")
    gdf_bus_joined = gdf_bus_joined.merge(
        stop_rid[["정류소명", "daily_boarding", "daily_alighting", "daily_total"]],
        on="정류소명",
        how="left"
    )
    
    gdf_bus_joined["pole_daily_boarding"] = (gdf_bus_joined["daily_boarding"].fillna(0.0) / gdf_bus_joined["pole_count"]).round(2)
    gdf_bus_joined["pole_daily_alighting"] = (gdf_bus_joined["daily_alighting"].fillna(0.0) / gdf_bus_joined["pole_count"]).round(2)
    gdf_bus_joined["pole_daily_total"] = (gdf_bus_joined["daily_total"].fillna(0.0) / gdf_bus_joined["pole_count"]).round(2)
    
    # 6. 행정동 단위 집계
    dong_bus_agg = gdf_bus_joined.groupby("adm_cd2").agg({
        "정류소명": "count",
        "pole_daily_boarding": "sum",
        "pole_daily_alighting": "sum",
        "pole_daily_total": "sum",
    }).rename(columns={
        "정류소명": "dong_bus_stop_count",
        "pole_daily_boarding": "dong_daily_bus_boarding",
        "pole_daily_alighting": "dong_daily_bus_alighting",
        "pole_daily_total": "dong_daily_bus_total"
    }).reset_index()
    
    # 150개 전체 행정동과 결합
    dong_features = df_dong_mart[["adm_cd2", "adm_nm", "area_km2"]].merge(dong_bus_agg, on="adm_cd2", how="left")
    dong_features["dong_bus_stop_count"] = dong_features["dong_bus_stop_count"].fillna(0).astype(int)
    dong_features["dong_daily_bus_boarding"] = dong_features["dong_daily_bus_boarding"].fillna(0.0).round(2)
    dong_features["dong_daily_bus_alighting"] = dong_features["dong_daily_bus_alighting"].fillna(0.0).round(2)
    dong_features["dong_daily_bus_total"] = dong_features["dong_daily_bus_total"].fillna(0.0).round(2)
    
    # 밀도 및 정류소당 승하차 지표 산출
    dong_features["dong_bus_stop_density"] = (dong_features["dong_bus_stop_count"] / dong_features["area_km2"]).round(2)
    dong_features["dong_bus_ridership_per_stop"] = (
        dong_features["dong_daily_bus_total"] / np.maximum(dong_features["dong_bus_stop_count"], 1)
    ).round(2)
    
    # 7. 점포 단위 최인접 버스 정류소 거리 산출 (cKDTree)
    if STORE_MART_PATH.exists():
        df_stores = pd.read_parquet(STORE_MART_PATH, columns=["bizesId", "adm_cd2", "x_utm", "y_utm"])
        tree = cKDTree(np.column_stack([bus_x, bus_y]))
        store_dists, _ = tree.query(np.column_stack([df_stores["x_utm"].values, df_stores["y_utm"].values]))
        df_stores["dist_to_bus"] = store_dists
        df_stores["is_bus_zone_300m"] = (store_dists <= 300.0).astype(int)
        
        store_dong_bus = df_stores.groupby("adm_cd2").agg(
            avg_dist_to_bus_m=("dist_to_bus", "mean"),
            ratio_stores_in_bus_300m=("is_bus_zone_300m", "mean")
        ).reset_index()
        
        dong_features = dong_features.merge(store_dong_bus, on="adm_cd2", how="left")
        dong_features["avg_dist_to_bus_m"] = dong_features["avg_dist_to_bus_m"].round(1)
        dong_features["ratio_stores_in_bus_300m"] = dong_features["ratio_stores_in_bus_300m"].round(4)
    else:
        dong_features["avg_dist_to_bus_m"] = 0.0
        dong_features["ratio_stores_in_bus_300m"] = 1.0
        
    # 무결성 검증
    if len(dong_features) != 150:
        raise ValueError(f"행정동 수가 150개가 아닙니다: {len(dong_features)}")
    if dong_features["dong_daily_bus_total"].isnull().sum() > 0:
        raise ValueError("버스 일평균 이용자수에 결측치가 있습니다.")
    if not (dong_features["dong_daily_bus_total"] >= 0).all():
        raise ValueError("음수 이용자수가 존재합니다.")
    
    # 저장
    if save:
        stop_cols_to_save = [
            "정류소명", "영문명", "시도", "구군", "동", "경도", "위도", "x_utm", "y_utm",
            "adm_cd2", "adm_nm", "경유노선수", "경유노선", "pole_count",
            "pole_daily_boarding", "pole_daily_alighting", "pole_daily_total"
        ]
        gdf_bus_joined[stop_cols_to_save].to_parquet(
            PROCESSED_BUS_DIR / "daegu_bus_stops_processed.parquet",
            index=False
        )
        
        dong_features.to_parquet(
            PROCESSED_BUS_DIR / "daegu_bus_dong_features.parquet",
            index=False
        )
        dong_features.to_csv(
            PROCESSED_BUS_DIR / "daegu_bus_dong_features.csv",
            index=False,
            encoding="utf-8-sig"
        )
        
    metadata = {
        **join_stats,
        "processed_stops_count": len(gdf_bus_joined),
        "total_dongs_covered": int((dong_features["dong_bus_stop_count"] > 0).sum()),
        "total_daily_bus_ridership": float(dong_features["dong_daily_bus_total"].sum()),
        "avg_daily_bus_ridership_per_dong": float(dong_features["dong_daily_bus_total"].mean()),
        "avg_bus_stops_per_dong": float(dong_features["dong_bus_stop_count"].mean()),
    }
    
    return gdf_bus_joined, dong_features, metadata

if __name__ == "__main__":
    print("Executing build_bus_feature_mart...")
    gdf_stops, df_dongs, meta = build_bus_feature_mart(save=True)
    print("Done! Metadata:")
    for k, v in meta.items():
        print(f"  {k}: {v}")
