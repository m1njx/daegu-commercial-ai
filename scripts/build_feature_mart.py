#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/build_feature_mart.py

Phase 4: 대구 상권 데이터 통합 + 공간분석 + Feature Mart 구축 파이프라인
- 이종 데이터 4종 통합:
  1) 상가업소 데이터 (118,357건)
  2) 도시철도 승하차 데이터 (94개 역, 2026.01~07 일별/시간별) + 역별 좌표
  3) 행정안전부 주민등록 인구 데이터 (150개 행정동, 연령대/성별)
  4) 대구광역시 부설주차장 공간 데이터 (4,765개소 SHP)
- 공간 참조계: WGS84 (EPSG:4326) -> UTM-K (EPSG:5179)
- cKDTree 기반 고속 공간 결합 및 반경 탐색
- 3개 수준 Feature Mart 산출:
  - Store Level: data/processed/feature_mart/store_spatial_features.parquet
  - Dong Level: data/processed/feature_mart/commercial_feature_mart_dong.parquet / .csv
  - Dong x Category Level: data/processed/feature_mart/commercial_feature_mart_dong_category.parquet / .csv
"""

import os
import sys
import time
import numpy as np
import pandas as pd
import geopandas as gpd
from pyproj import Transformer
from scipy.spatial import cKDTree
from shapely.geometry import Point

def log(msg: str):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

def main():
    start_time = time.time()
    log("=== [PHASE 4] 대구 상권 통합 공간 Feature Mart 구축 시작 ===")

    # 0. 경로 설정
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    comm_path = os.path.join(base_dir, "data/raw/commercial/소상공인시장진흥공단_상가상권정보/소상공인시장진흥공단_상가업소정보_대구_20260907.csv")
    subway_path = os.path.join(base_dir, "data/raw/subway/대구교통공사_역별일별시간별승하차/대구교통공사_역별일별시간별승하차인원현황_20260731.csv")
    station_coord_path = os.path.join(base_dir, "data/processed/transit/대구도시철도_역별_위경도좌표.csv")
    pop_path = os.path.join(base_dir, "data/raw/population/행정안전부_지역별행정동_성별연령별인구/행정안전부_지역별(행정동) 성별 연령별 주민등록 인구수_20260731.csv")
    parking_path = os.path.join(base_dir, "data/raw/parking/대구광역시_부설주차장/대구부설주차장정보.shp")
    geojson_path = os.path.join(base_dir, "data/processed/geojson/대구_행정동_경계_20230701.geojson")

    output_dir = os.path.join(base_dir, "data/processed/feature_mart")
    os.makedirs(output_dir, exist_ok=True)

    transformer = Transformer.from_crs("EPSG:4326", "EPSG:5179", always_xy=True)

    # 1. 행정동 경계 데이터 로드 및 면적 계산
    log("1. 행정동 경계 GeoJSON 로드 및 면적(km2) 계산")
    gdf_dong = gpd.read_file(geojson_path)
    gdf_dong_proj = gdf_dong.to_crs("EPSG:5179")
    gdf_dong["area_km2"] = (gdf_dong_proj.area / 1e6).round(4)
    gdf_dong["adm_cd2"] = gdf_dong["adm_cd2"].astype(str)
    log(f"   -> 총 {len(gdf_dong)}개 행정동 로드 완료 (총 면적: {gdf_dong['area_km2'].sum():.2f} km²)")

    # 2. 도시철도 승하차 통계 집계 및 공간 매핑
    log("2. 도시철도 94개 역 일별/시간별 승하차 통계 집계")
    df_subway = pd.read_csv(subway_path, encoding="cp949")
    df_coords = pd.read_csv(station_coord_path, encoding="utf-8-sig")

    df_subway["date"] = pd.to_datetime(
        "2026-" + df_subway["월"].astype(str).str.zfill(2) + "-" + df_subway["일"].astype(str).str.zfill(2)
    )
    df_subway["is_weekend"] = df_subway["date"].dt.dayofweek >= 5
    df_subway["commute_morning"] = df_subway["07시-08시"] + df_subway["08시-09시"]
    df_subway["commute_evening"] = df_subway["17시-18시"] + df_subway["18시-19시"] + df_subway["19시-20시"]
    df_subway["lunch_time"] = df_subway["11시-12시"] + df_subway["12시-13시"] + df_subway["13시-14시"]

    # 일별 역별 총합(승차+하차) 집계
    daily_station = df_subway.groupby(["역번호", "역명", "date", "is_weekend"]).agg(
        daily_total=("일계", "sum"),
        morning_total=("commute_morning", "sum"),
        evening_total=("commute_evening", "sum"),
        lunch_total=("lunch_time", "sum"),
    ).reset_index()

    station_summary = daily_station.groupby(["역번호", "역명"]).agg(
        daily_ridership_mean=("daily_total", "mean"),
        morning_commute_mean=("morning_total", "mean"),
        evening_commute_mean=("evening_total", "mean"),
        lunch_flow_mean=("lunch_total", "mean"),
    ).reset_index()

    weekend_flow = daily_station[daily_station["is_weekend"]].groupby("역번호")["daily_total"].mean()
    weekday_flow = daily_station[~daily_station["is_weekend"]].groupby("역번호")["daily_total"].mean()
    station_summary["weekend_weekday_ratio"] = (
        station_summary["역번호"].map(weekend_flow / weekday_flow).round(4)
    )

    station_summary = station_summary.merge(
        df_coords[["역번호", "호선", "lon", "lat"]], on="역번호", how="left"
    )

    # 역 투영좌표 계산
    sub_x, sub_y = transformer.transform(station_summary["lon"].values, station_summary["lat"].values)
    station_summary["x_utm"] = sub_x
    station_summary["y_utm"] = sub_y

    # 동 내부 역 집계 (Point-in-polygon)
    sub_pts = [Point(xy) for xy in zip(station_summary["lon"], station_summary["lat"])]
    gdf_sub = gpd.GeoDataFrame(station_summary, geometry=sub_pts, crs="EPSG:4326")
    sub_in_dong = gpd.sjoin(gdf_sub, gdf_dong[["adm_cd2", "geometry"]], how="inner", predicate="within")

    dong_sub_agg = sub_in_dong.groupby("adm_cd2").agg(
        dong_station_count=("역번호", "count"),
        dong_daily_ridership=("daily_ridership_mean", "sum"),
        dong_station_names=("역명", lambda x: ", ".join(sorted(set(x)))),
    ).reset_index()
    log(f"   -> 도시철도 94개 역 집계 완료. 대구 관내 행정동 내 위치 역: {len(sub_in_dong)}개")

    # 3. 부설주차장 데이터 로드 및 공간 집계
    log("3. 부설주차장(4,765개소) 로드 및 공간 집계")
    gdf_parking = gpd.read_file(parking_path)
    if gdf_parking.crs != "EPSG:4326":
        gdf_parking = gdf_parking.to_crs("EPSG:4326")

    gdf_parking["P_SURFACE"] = pd.to_numeric(gdf_parking["P_SURFACE"], errors="coerce").fillna(10).astype(int)
    park_x, park_y = transformer.transform(gdf_parking.geometry.x.values, gdf_parking.geometry.y.values)
    gdf_parking["x_utm"] = park_x
    gdf_parking["y_utm"] = park_y

    # 동 경계 내부 주차장 집계
    park_in_dong = gpd.sjoin(gdf_parking, gdf_dong[["adm_cd2", "geometry"]], how="inner", predicate="within")
    dong_park_agg = park_in_dong.groupby("adm_cd2").agg(
        dong_parking_lot_count=("PARK_ID", "count"),
        dong_total_parking_capacity=("P_SURFACE", "sum"),
    ).reset_index()
    log(f"   -> 주차장 {len(gdf_parking)}개소 동 경계 매핑 완료 (총 주차면수: {gdf_parking['P_SURFACE'].sum():,}면)")

    # 4. 주민등록 인구 데이터 집계 (150개 동 매핑)
    log("4. 주민등록 인구 데이터 집계 및 연령구조 피처 엔지니어링")
    df_pop = pd.read_csv(pop_path, encoding="cp949")
    daegu_pop = df_pop[df_pop["시도명"] == "대구광역시"].copy()

    # 출장소 코드 부모 읍면동으로 매핑
    remap = {"2771025400": "2771025300", "2771025700": "2771025600"}
    daegu_pop["adm_cd2"] = daegu_pop["행정기관코드"].astype(str).replace(remap)

    m_0_19 = [f"{i}세남자" for i in range(20)]
    f_0_19 = [f"{i}세여자" for i in range(20)]
    m_20s = [f"{i}세남자" for i in range(20, 30)]
    f_20s = [f"{i}세여자" for i in range(20, 30)]
    m_30s = [f"{i}세남자" for i in range(30, 40)]
    f_30s = [f"{i}세여자" for i in range(30, 40)]
    m_40s = [f"{i}세남자" for i in range(40, 50)]
    f_40s = [f"{i}세여자" for i in range(40, 50)]
    m_50s = [f"{i}세남자" for i in range(50, 60)]
    f_50s = [f"{i}세여자" for i in range(50, 60)]
    m_60plus = [f"{i}세남자" for i in range(60, 110)] + ["110세이상 남자"]
    f_60plus = [f"{i}세여자" for i in range(60, 110)] + ["110세이상 여자"]

    daegu_pop["pop_under20"] = daegu_pop[m_0_19 + f_0_19].sum(axis=1)
    daegu_pop["pop_20s"] = daegu_pop[m_20s + f_20s].sum(axis=1)
    daegu_pop["pop_30s"] = daegu_pop[m_30s + f_30s].sum(axis=1)
    daegu_pop["pop_40s"] = daegu_pop[m_40s + f_40s].sum(axis=1)
    daegu_pop["pop_50s"] = daegu_pop[m_50s + f_50s].sum(axis=1)
    daegu_pop["pop_60plus"] = daegu_pop[m_60plus + f_60plus].sum(axis=1)

    pop_agg = daegu_pop.groupby("adm_cd2").agg(
        pop_total=("계", "sum"),
        pop_male=("남자", "sum"),
        pop_female=("여자", "sum"),
        pop_under20=("pop_under20", "sum"),
        pop_20s=("pop_20s", "sum"),
        pop_30s=("pop_30s", "sum"),
        pop_40s=("pop_40s", "sum"),
        pop_50s=("pop_50s", "sum"),
        pop_60plus=("pop_60plus", "sum"),
    ).reset_index()

    pop_agg["sex_ratio"] = (pop_agg["pop_male"] / pop_agg["pop_female"] * 100).round(2)
    pop_agg["ratio_2030"] = ((pop_agg["pop_20s"] + pop_agg["pop_30s"]) / pop_agg["pop_total"]).round(4)
    pop_agg["ratio_4050"] = ((pop_agg["pop_40s"] + pop_agg["pop_50s"]) / pop_agg["pop_total"]).round(4)
    pop_agg["ratio_60plus"] = (pop_agg["pop_60plus"] / pop_agg["pop_total"]).round(4)
    log(f"   -> 대구 150개 행정동 인구 집계 완료 (총 인구: {pop_agg['pop_total'].sum():,}명)")

    # 5. 상가업소 데이터 로드 및 점포 단위 공간 피처 엔지니어링
    log("5. 상가업소(118,357건) 로드 및 공간 피처(지하철, 주차장, 경쟁 점포) 계산")
    df_comm = pd.read_csv(comm_path, low_memory=False)
    log(f"   -> 상가업소 원본: {len(df_comm)}건")

    # 행정동코드 10자리 정규화
    df_comm["adm_cd2"] = df_comm["adongCd"].astype(str) + "00"

    # 좌표 투영
    comm_x, comm_y = transformer.transform(df_comm["lon"].values, df_comm["lat"].values)
    df_comm["x_utm"] = comm_x
    df_comm["y_utm"] = comm_y
    store_coords = np.column_stack([comm_x, comm_y])

    # 5.1 지하철역 공간 결합 (cKDTree)
    log("   5.1 최인접 지하철역 거리 및 승하차 유동 피처 결합")
    subway_coords = np.column_stack([station_summary["x_utm"].values, station_summary["y_utm"].values])
    subway_tree = cKDTree(subway_coords)
    sub_dists, sub_idxs = subway_tree.query(store_coords, k=1)

    matched_stations = station_summary.iloc[sub_idxs].reset_index(drop=True)
    df_comm["nearest_subway_dist_m"] = np.round(sub_dists, 1)
    df_comm["nearest_subway_id"] = matched_stations["역번호"].values
    df_comm["nearest_subway_name"] = matched_stations["역명"].values
    df_comm["nearest_subway_line"] = matched_stations["호선"].values
    df_comm["nearest_subway_daily_ridership"] = np.round(matched_stations["daily_ridership_mean"].values, 1)
    df_comm["nearest_subway_morning_flow"] = np.round(matched_stations["morning_commute_mean"].values, 1)
    df_comm["nearest_subway_evening_flow"] = np.round(matched_stations["evening_commute_mean"].values, 1)
    df_comm["nearest_subway_lunch_flow"] = np.round(matched_stations["lunch_flow_mean"].values, 1)
    df_comm["nearest_subway_weekend_ratio"] = matched_stations["weekend_weekday_ratio"].values

    # 역세권 구분
    conditions = [
        df_comm["nearest_subway_dist_m"] <= 300,
        df_comm["nearest_subway_dist_m"] <= 500,
    ]
    choices = ["초역세권", "역세권"]
    df_comm["subway_zone_type"] = np.select(conditions, choices, default="비역세권")
    df_comm["is_subway_zone"] = (df_comm["nearest_subway_dist_m"] <= 500).astype(int)

    # 5.2 부설주차장 공간 결합 (cKDTree)
    log("   5.2 최인접 부설주차장 및 반경 300m/500m 수용능력 피처 결합")
    parking_coords = np.column_stack([gdf_parking["x_utm"].values, gdf_parking["y_utm"].values])
    parking_caps = gdf_parking["P_SURFACE"].values
    parking_tree = cKDTree(parking_coords)

    park_dists, park_idxs = parking_tree.query(store_coords, k=1)
    df_comm["nearest_parking_dist_m"] = np.round(park_dists, 1)
    df_comm["nearest_parking_capacity"] = parking_caps[park_idxs]

    # 반경 300m / 500m 쿼리
    log("       -> 주차장 반경 300m 탐색...")
    ball_300 = parking_tree.query_ball_point(store_coords, r=300)
    df_comm["parking_count_300m"] = [len(x) for x in ball_300]
    df_comm["parking_capacity_300m"] = [parking_caps[x].sum() if len(x) > 0 else 0 for x in ball_300]

    log("       -> 주차장 반경 500m 탐색...")
    ball_500 = parking_tree.query_ball_point(store_coords, r=500)
    df_comm["parking_count_500m"] = [len(x) for x in ball_500]
    df_comm["parking_capacity_500m"] = [parking_caps[x].sum() if len(x) > 0 else 0 for x in ball_500]

    # 5.3 업종별 반경 내 경쟁 점포 수 계산 (업종대분류 및 업종중분류)
    log("   5.3 업종별 반경 300m/500m 마이크로 경쟁 점포 수 계산")
    comp_lcls_300 = np.zeros(len(df_comm), dtype=int)
    comp_lcls_500 = np.zeros(len(df_comm), dtype=int)
    for lcls in df_comm["indsLclsNm"].unique():
        idx = np.where(df_comm["indsLclsNm"].values == lcls)[0]
        pts = store_coords[idx]
        if len(pts) > 1:
            tree = cKDTree(pts)
            b300 = tree.query_ball_point(pts, r=300)
            b500 = tree.query_ball_point(pts, r=500)
            comp_lcls_300[idx] = [len(x) - 1 for x in b300]
            comp_lcls_500[idx] = [len(x) - 1 for x in b500]

    df_comm["competitor_lcls_count_300m"] = comp_lcls_300
    df_comm["competitor_lcls_count_500m"] = comp_lcls_500

    comp_mcls_300 = np.zeros(len(df_comm), dtype=int)
    comp_mcls_500 = np.zeros(len(df_comm), dtype=int)
    for mcls in df_comm["indsMclsNm"].unique():
        idx = np.where(df_comm["indsMclsNm"].values == mcls)[0]
        pts = store_coords[idx]
        if len(pts) > 1:
            tree = cKDTree(pts)
            b300 = tree.query_ball_point(pts, r=300)
            b500 = tree.query_ball_point(pts, r=500)
            comp_mcls_300[idx] = [len(x) - 1 for x in b300]
            comp_mcls_500[idx] = [len(x) - 1 for x in b500]

    df_comm["competitor_mcls_count_300m"] = comp_mcls_300
    df_comm["competitor_mcls_count_500m"] = comp_mcls_500

    # 5.4 점포 단위 Feature Mart 저장
    store_features = df_comm[[
        "bizesId", "bizesNm", "indsLclsCd", "indsLclsNm", "indsMclsCd", "indsMclsNm",
        "indsSclsCd", "indsSclsNm", "ctprvnNm", "signguCd", "signguNm", "adongCd", "adongNm",
        "adm_cd2", "lon", "lat", "x_utm", "y_utm",
        "nearest_subway_dist_m", "nearest_subway_id", "nearest_subway_name", "nearest_subway_line",
        "nearest_subway_daily_ridership", "nearest_subway_morning_flow", "nearest_subway_evening_flow",
        "nearest_subway_lunch_flow", "nearest_subway_weekend_ratio", "subway_zone_type", "is_subway_zone",
        "nearest_parking_dist_m", "nearest_parking_capacity",
        "parking_count_300m", "parking_capacity_300m", "parking_count_500m", "parking_capacity_500m",
        "competitor_lcls_count_300m", "competitor_lcls_count_500m",
        "competitor_mcls_count_300m", "competitor_mcls_count_500m"
    ]].copy()

    store_out_parquet = os.path.join(output_dir, "store_spatial_features.parquet")
    store_features.to_parquet(store_out_parquet, index=False)
    log(f"   -> [저장 완료] 점포 단위 공간 피처: {store_out_parquet} ({len(store_features):,}건)")

    # 6. 행정동 단위 종합 Feature Mart 구축
    log("6. 행정동 단위(150개 동) 종합 Feature Mart 구축")
    # 동별 점포 수 및 업종별 점포 수
    dong_store_counts = df_comm.groupby("adm_cd2").agg(
        total_stores=("bizesId", "count"),
        avg_dist_to_subway_m=("nearest_subway_dist_m", "mean"),
        ratio_stores_in_subway_zone=("is_subway_zone", "mean"),
        avg_dist_to_parking_m=("nearest_parking_dist_m", "mean"),
        avg_parking_capacity_300m=("parking_capacity_300m", "mean"),
    ).reset_index()

    # 업종 다양성 지수 (Shannon Entropy & HHI)
    def calc_diversity(sub_df):
        counts = sub_df["indsLclsNm"].value_counts().values
        props = counts / counts.sum()
        entropy = -np.sum(props * np.log(props + 1e-12))
        hhi = np.sum(props ** 2)
        top_lcls = sub_df["indsLclsNm"].value_counts().index[0]
        top_mcls = sub_df["indsMclsNm"].value_counts().index[0]
        return pd.Series({
            "category_entropy": round(entropy, 4),
            "category_hhi": round(hhi, 4),
            "top_industry_lcls": top_lcls,
            "top_industry_mcls": top_mcls,
        })

    log("   -> 행정동별 업종 다양성(Shannon Entropy, HHI) 계산...")
    dong_diversity = df_comm.groupby("adm_cd2").apply(calc_diversity, include_groups=False).reset_index()

    # 대분류별 점포 수 피벗
    lcls_pivot = df_comm.pivot_table(
        index="adm_cd2", columns="indsLclsNm", values="bizesId", aggfunc="count", fill_value=0
    )
    lcls_pivot.columns = [f"stores_{c}" for c in lcls_pivot.columns]
    lcls_pivot = lcls_pivot.reset_index()

    # 결합: gdf_dong + pop_agg + dong_sub_agg + dong_park_agg + dong_store_counts + dong_diversity + lcls_pivot
    dong_mart = gdf_dong[["adm_cd2", "adm_nm", "sgg", "sggnm", "area_km2"]].copy()
    dong_mart.rename(columns={"sgg": "signgu_cd", "sggnm": "signgu_nm"}, inplace=True)

    dong_mart = dong_mart.merge(pop_agg, on="adm_cd2", how="left")
    dong_mart = dong_mart.merge(dong_store_counts, on="adm_cd2", how="left")
    dong_mart = dong_mart.merge(dong_diversity, on="adm_cd2", how="left")
    dong_mart = dong_mart.merge(lcls_pivot, on="adm_cd2", how="left")
    dong_mart = dong_mart.merge(dong_sub_agg, on="adm_cd2", how="left")
    dong_mart = dong_mart.merge(dong_park_agg, on="adm_cd2", how="left")

    # 결측치 정제
    dong_mart["total_stores"] = dong_mart["total_stores"].fillna(0).astype(int)
    dong_mart["pop_total"] = dong_mart["pop_total"].fillna(0).astype(int)
    dong_mart["dong_station_count"] = dong_mart["dong_station_count"].fillna(0).astype(int)
    dong_mart["dong_daily_ridership"] = dong_mart["dong_daily_ridership"].fillna(0).round(1)
    dong_mart["dong_station_names"] = dong_mart["dong_station_names"].fillna("없음")
    dong_mart["dong_parking_lot_count"] = dong_mart["dong_parking_lot_count"].fillna(0).astype(int)
    dong_mart["dong_total_parking_capacity"] = dong_mart["dong_total_parking_capacity"].fillna(0).astype(int)

    # 파생 지표
    dong_mart["pop_density"] = (dong_mart["pop_total"] / dong_mart["area_km2"]).round(1)
    dong_mart["store_density_km2"] = (dong_mart["total_stores"] / dong_mart["area_km2"]).round(1)
    dong_mart["stores_per_1000_pop"] = np.where(
        dong_mart["pop_total"] > 0,
        (dong_mart["total_stores"] / (dong_mart["pop_total"] / 1000)).round(2),
        0.0,
    )
    dong_mart["parking_capacity_per_store"] = np.where(
        dong_mart["total_stores"] > 0,
        (dong_mart["dong_total_parking_capacity"] / dong_mart["total_stores"]).round(2),
        0.0,
    )
    dong_mart["parking_capacity_per_1000_pop"] = np.where(
        dong_mart["pop_total"] > 0,
        (dong_mart["dong_total_parking_capacity"] / (dong_mart["pop_total"] / 1000)).round(2),
        0.0,
    )

    dong_mart["avg_dist_to_subway_m"] = dong_mart["avg_dist_to_subway_m"].round(1)
    dong_mart["ratio_stores_in_subway_zone"] = dong_mart["ratio_stores_in_subway_zone"].round(4)
    dong_mart["avg_dist_to_parking_m"] = dong_mart["avg_dist_to_parking_m"].round(1)
    dong_mart["avg_parking_capacity_300m"] = dong_mart["avg_parking_capacity_300m"].round(1)

    dong_out_parquet = os.path.join(output_dir, "commercial_feature_mart_dong.parquet")
    dong_out_csv = os.path.join(output_dir, "commercial_feature_mart_dong.csv")
    dong_mart.to_parquet(dong_out_parquet, index=False)
    dong_mart.to_csv(dong_out_csv, index=False, encoding="utf-8-sig")
    log(f"   -> [저장 완료] 행정동 단위 Feature Mart: {dong_out_parquet} ({len(dong_mart)}개 행정동)")

    # 7. 행정동 x 업종대분류 단위 Feature Mart 구축
    log("7. 행정동 x 업종대분류(Dong x Category) 단위 Feature Mart 구축")
    city_total_stores = len(df_comm)
    city_lcls_totals = df_comm["indsLclsNm"].value_counts().to_dict()

    # 동-업종 집계
    cat_agg = df_comm.groupby(["adm_cd2", "indsLclsCd", "indsLclsNm"]).agg(
        store_count=("bizesId", "count"),
        avg_nearest_subway_dist_m=("nearest_subway_dist_m", "mean"),
        ratio_subway_zone=("is_subway_zone", "mean"),
        avg_parking_capacity_300m=("parking_capacity_300m", "mean"),
        avg_competitor_lcls_300m=("competitor_lcls_count_300m", "mean"),
        avg_competitor_mcls_300m=("competitor_mcls_count_300m", "mean"),
    ).reset_index()

    # 동 메타정보 머지
    cat_mart = cat_agg.merge(
        dong_mart[[
            "adm_cd2", "adm_nm", "signgu_cd", "signgu_nm", "area_km2",
            "pop_total", "pop_density", "sex_ratio", "ratio_2030", "ratio_4050", "ratio_60plus",
            "total_stores", "dong_station_count", "dong_daily_ridership",
            "dong_parking_lot_count", "dong_total_parking_capacity"
        ]],
        on="adm_cd2",
        how="left"
    )

    # 지표 계산: 비중, 밀도, 입지계수(LQ), 인구당 점포수
    cat_mart["store_share_in_dong"] = (cat_mart["store_count"] / cat_mart["total_stores"]).round(4)
    cat_mart["store_share_in_city"] = (
        cat_mart["store_count"] / cat_mart["indsLclsNm"].map(city_lcls_totals)
    ).round(4)

    # LQ = (해당동 업종점포수 / 해당동 총점포수) / (시전체 업종점포수 / 시전체 총점포수)
    city_lcls_share = cat_mart["indsLclsNm"].map(
        {k: v / city_total_stores for k, v in city_lcls_totals.items()}
    )
    cat_mart["location_quotient"] = (
        (cat_mart["store_count"] / cat_mart["total_stores"]) / city_lcls_share
    ).round(3)

    cat_mart["store_density_km2"] = (cat_mart["store_count"] / cat_mart["area_km2"]).round(2)
    cat_mart["stores_per_1000_pop"] = np.where(
        cat_mart["pop_total"] > 0,
        (cat_mart["store_count"] / (cat_mart["pop_total"] / 1000)).round(2),
        0.0,
    )

    cat_mart["avg_nearest_subway_dist_m"] = cat_mart["avg_nearest_subway_dist_m"].round(1)
    cat_mart["ratio_subway_zone"] = cat_mart["ratio_subway_zone"].round(4)
    cat_mart["avg_parking_capacity_300m"] = cat_mart["avg_parking_capacity_300m"].round(1)
    cat_mart["avg_competitor_lcls_300m"] = cat_mart["avg_competitor_lcls_300m"].round(1)
    cat_mart["avg_competitor_mcls_300m"] = cat_mart["avg_competitor_mcls_300m"].round(1)

    cat_out_parquet = os.path.join(output_dir, "commercial_feature_mart_dong_category.parquet")
    cat_out_csv = os.path.join(output_dir, "commercial_feature_mart_dong_category.csv")
    cat_mart.to_parquet(cat_out_parquet, index=False)
    cat_mart.to_csv(cat_out_csv, index=False, encoding="utf-8-sig")
    log(f"   -> [저장 완료] 행정동 x 업종 Feature Mart: {cat_out_parquet} ({len(cat_mart):,}개 조합)")

    elapsed = time.time() - start_time
    log(f"=== [PHASE 4 완료] Feature Mart 파이프라인 정상 완료 (소요시간: {elapsed:.1f}초) ===")

if __name__ == "__main__":
    main()
