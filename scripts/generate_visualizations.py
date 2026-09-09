#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/generate_visualizations.py

Phase 4: 대구 상권 공간 Feature Mart 시각화 아티팩트 생성 스크립트
1) store_density_map.png: 대구 행정동별 점포 밀도 코로플레스 + 도시철도 역 오버레이
2) industry_distribution_by_district.png: 대구 9개 구·군별 10대 업종대분류 점포 수 및 비중 분포
3) transit_accessibility_distribution.png: 역세권 접근성 분포, 거리별 점포 비중, 주요 역 유동인구
4) parking_capacity_vs_stores.png: 행정동별 주차 수용용량 vs 점포 수 산점도 및 주차 수급 격차 분석
"""

import os
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd
import geopandas as gpd

def setup_matplotlib():
    plt.rcParams["font.family"] = "AppleGothic"
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 300

def generate_visualizations():
    setup_matplotlib()
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    mart_dir = os.path.join(base_dir, "data/processed/feature_mart")
    fig_dir = os.path.join(base_dir, "reports/figures")
    os.makedirs(fig_dir, exist_ok=True)

    geojson_path = os.path.join(base_dir, "data/processed/geojson/대구_행정동_경계_20230701.geojson")
    transit_path = os.path.join(base_dir, "data/processed/transit/대구도시철도_역별_위경도좌표.csv")

    print("[VISUALIZATION] 데이터셋 로드 중...")
    df_dong = pd.read_parquet(os.path.join(mart_dir, "commercial_feature_mart_dong.parquet"))
    df_store = pd.read_parquet(os.path.join(mart_dir, "store_spatial_features.parquet"))
    df_cat = pd.read_parquet(os.path.join(mart_dir, "commercial_feature_mart_dong_category.parquet"))
    gdf_dong = gpd.read_file(geojson_path)
    df_transit = pd.read_csv(transit_path, encoding="utf-8-sig")

    # GeoJSON에 피처 결합
    gdf_dong["adm_cd2"] = gdf_dong["adm_cd2"].astype(str)
    gdf_merged = gdf_dong.merge(
        df_dong[["adm_cd2", "total_stores", "store_density_km2", "pop_density", "dong_total_parking_capacity"]],
        on="adm_cd2",
        how="left"
    )

    # ----------------------------------------------------
    # Figure 1: 대구 행정동별 점포 밀도 및 도시철도 노선망 지도
    # ----------------------------------------------------
    print("[1/4] store_density_map.png 생성 중...")
    fig, ax = plt.subplots(figsize=(12, 11))
    
    # 군위군 포함 대구 전역 코로플레스 (밀도는 로그 스케일 적용하여 도심과 외곽 균형 표현)
    gdf_merged["log_density"] = np.log1p(gdf_merged["store_density_km2"])
    gdf_merged.plot(
        column="store_density_km2",
        ax=ax,
        cmap="YlOrRd",
        legend=True,
        legend_kwds={
            "label": "점포 밀도 (개소/km²)",
            "orientation": "horizontal",
            "shrink": 0.5,
            "pad": 0.02
        },
        edgecolor="#888888",
        linewidth=0.4,
        norm=mcolors.LogNorm(vmin=1, vmax=gdf_merged["store_density_km2"].max())
    )

    # 도시철도 역 오버레이 (호선별 색상)
    line_colors = {1: "#D93F36", 2: "#00A84D", 3: "#FAB131"}
    for line, color in line_colors.items():
        sub_line = df_transit[df_transit["호선"] == line]
        ax.scatter(
            sub_line["lon"], sub_line["lat"],
            c=color, s=24, edgecolors="white", linewidths=0.6,
            label=f"도시철도 {line}호선 ({len(sub_line)}개 역)", zorder=5
        )

    # 상위 밀도 주요 행정동 텍스트 표기
    top_label_dongs = ["대신동", "성내1동", "성내2동", "삼덕동", "신당동", "범어동", "동천동"]
    for _, row in gdf_merged.iterrows():
        adm_short = row["adm_nm"].split()[-1]
        if adm_short in top_label_dongs:
            pt = row.geometry.centroid
            ax.annotate(
                adm_short,
                xy=(pt.x, pt.y),
                xytext=(3, 3),
                textcoords="offset points",
                fontsize=8.5,
                fontweight="bold",
                color="#111111",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8, edgecolor="#aaaaaa", lw=0.5)
            )

    ax.set_title("대구광역시 행정동별 점포 밀도(코로플레스) 및 도시철도 노선망 공간 분포", fontsize=14, fontweight="bold", pad=12)
    ax.set_xlabel("경도 (Longitude, WGS84)", fontsize=10)
    ax.set_ylabel("위도 (Latitude, WGS84)", fontsize=10)
    ax.legend(loc="lower left", frameon=True, facecolor="white", framealpha=0.9, fontsize=9)
    ax.grid(True, linestyle="--", alpha=0.3)
    plt.tight_layout()
    fig1_path = os.path.join(fig_dir, "store_density_map.png")
    fig.savefig(fig1_path, dpi=300)
    plt.close(fig)
    print(f"   -> 저장 완료: {fig1_path}")

    # ----------------------------------------------------
    # Figure 2: 9개 구·군별 10대 업종대분류 점포 수 및 구성비
    # ----------------------------------------------------
    print("[2/4] industry_distribution_by_district.png 생성 중...")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

    district_order = ["중구", "동구", "서구", "남구", "북구", "수성구", "달서구", "달성군", "군위군"]
    industry_order = df_store["indsLclsNm"].value_counts().index.tolist()

    # 구별 업종별 점포 수 피벗
    dist_lcls = df_store.pivot_table(
        index="signguNm", columns="indsLclsNm", values="bizesId", aggfunc="count", fill_value=0
    ).reindex(district_order)
    dist_lcls = dist_lcls[industry_order]

    # 누적 절대 점포수 (ax1)
    dist_lcls.plot(kind="bar", stacked=True, ax=ax1, colormap="tab10", width=0.7)
    ax1.set_title("대구 구·군별 10대 업종 점포 수 (절대 규모)", fontsize=12, fontweight="bold")
    ax1.set_xlabel("자치구·군", fontsize=10)
    ax1.set_ylabel("점포 수 (개소)", fontsize=10)
    ax1.legend(loc="upper right", title="업종대분류", fontsize=8, title_fontsize=9)
    ax1.grid(axis="y", linestyle="--", alpha=0.4)
    ax1.tick_params(axis="x", rotation=0)

    # 100% 비중 누적 막대 (ax2)
    dist_lcls_pct = dist_lcls.div(dist_lcls.sum(axis=1), axis=0) * 100
    dist_lcls_pct.plot(kind="bar", stacked=True, ax=ax2, colormap="tab10", width=0.7, legend=False)
    ax2.set_title("대구 구·군별 업종 구성 비중 (상대 구성비 %)", fontsize=12, fontweight="bold")
    ax2.set_xlabel("자치구·군", fontsize=10)
    ax2.set_ylabel("업종 구성비 (%)", fontsize=10)
    ax2.grid(axis="y", linestyle="--", alpha=0.4)
    ax2.tick_params(axis="x", rotation=0)
    ax2.set_ylim(0, 100)

    fig.suptitle("대구광역시 자치구·군별 상권 업종 분포 및 산업 구조 비교", fontsize=14, fontweight="bold", y=0.98)
    plt.tight_layout()
    fig2_path = os.path.join(fig_dir, "industry_distribution_by_district.png")
    fig.savefig(fig2_path, dpi=300)
    plt.close(fig)
    print(f"   -> 저장 완료: {fig2_path}")

    # ----------------------------------------------------
    # Figure 3: 지하철 접근성 및 유동인구 다차원 분석
    # ----------------------------------------------------
    print("[3/4] transit_accessibility_distribution.png 생성 중...")
    fig, axes = plt.subplots(2, 2, figsize=(14, 11))

    # (A) 지하철역까지의 거리 분포 히스토그램 (5000m 이내)
    ax_a = axes[0, 0]
    clip_dist = df_store["nearest_subway_dist_m"].clip(upper=3000)
    ax_a.hist(clip_dist, bins=40, color="#3470A3", edgecolor="white", alpha=0.85)
    ax_a.axvline(300, color="#E63946", linestyle="--", linewidth=1.5, label="초역세권 임계선 (300m)")
    ax_a.axvline(500, color="#F4A261", linestyle="--", linewidth=1.5, label="역세권 임계선 (500m)")
    ax_a.set_title("(A) 점포별 최인접 지하철역 거리 분포 (3km 이내)", fontsize=11, fontweight="bold")
    ax_a.set_xlabel("거리 (미터)", fontsize=9.5)
    ax_a.set_ylabel("점포 수 (개소)", fontsize=9.5)
    ax_a.legend(loc="upper right", fontsize=8.5)
    ax_a.grid(True, linestyle="--", alpha=0.3)

    # (B) 역세권 권역별 점포 수 및 비중 파이차트
    ax_b = axes[0, 1]
    zone_counts = df_store["subway_zone_type"].value_counts()[["초역세권", "역세권", "비역세권"]]
    colors = ["#E63946", "#F4A261", "#8D99AE"]
    explode = (0.05, 0.03, 0)
    ax_b.pie(
        zone_counts,
        labels=[f"{k}\n({v:,}건)" for k, v in zone_counts.items()],
        autopct="%1.1f%%",
        startangle=140,
        colors=colors,
        explode=explode,
        textprops={"fontsize": 9.5, "fontweight": "bold"}
    )
    ax_b.set_title("(B) 대구시 전체 점포의 역세권 입지 분류", fontsize=11, fontweight="bold")

    # (C) 상위 10개 최다 승하차 역 일평균 유동인구
    ax_c = axes[1, 0]
    station_flow = df_store.groupby(["nearest_subway_name", "nearest_subway_line"]).agg(
        ridership=("nearest_subway_daily_ridership", "first"),
        nearby_stores=("bizesId", "count")
    ).reset_index().sort_values("ridership", ascending=False).head(10)

    bars = ax_c.barh(
        station_flow["nearest_subway_name"] + f" ({station_flow['nearest_subway_line'].astype(str)}호선)",
        station_flow["ridership"] / 1000,
        color="#2A9D8F", edgecolor="white", height=0.65
    )
    ax_c.invert_yaxis()
    ax_c.set_title("(C) 일평균 승하차 상위 10개 역 (일평균 유동인구)", fontsize=11, fontweight="bold")
    ax_c.set_xlabel("일평균 승하차객수 (천 명/일)", fontsize=9.5)
    ax_c.grid(axis="x", linestyle="--", alpha=0.3)
    for bar in bars:
        ax_c.text(
            bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
            f"{bar.get_width():.1f}k", va="center", fontsize=8.5, fontweight="bold"
        )

    # (D) 주요 도심역 시간대별 유동 패턴 비교 (반월당, 동대구역, 중앙로)
    ax_d = axes[1, 1]
    focus_stations = ["반월당1", "동대구역", "중앙로", "상인"]
    focus_data = df_store[df_store["nearest_subway_name"].isin(focus_stations)].groupby("nearest_subway_name").agg(
        morning=("nearest_subway_morning_flow", "first"),
        lunch=("nearest_subway_lunch_flow", "first"),
        evening=("nearest_subway_evening_flow", "first"),
    ).loc[focus_stations]

    time_slots = ["출근시간대\n(07~09시)", "점심시간대\n(11~14시)", "퇴근시간대\n(17~20시)"]
    x = np.arange(len(time_slots))
    width = 0.2
    for i, stn in enumerate(focus_stations):
        ax_d.bar(
            x + (i - 1.5) * width,
            focus_data.loc[stn] / 1000,
            width=width,
            label=stn
        )
    ax_d.set_xticks(x)
    ax_d.set_xticklabels(time_slots, fontsize=9)
    ax_d.set_title("(D) 핵심 도심 역사별 주요 시간대 승하차객 비교", fontsize=11, fontweight="bold")
    ax_d.set_ylabel("시간대별 승하차객 (천 명)", fontsize=9.5)
    ax_d.legend(loc="upper left", fontsize=8.5)
    ax_d.grid(axis="y", linestyle="--", alpha=0.3)

    fig.suptitle("대구 상권 대중교통(도시철도) 접근성 및 시간대별 유동인구 구조", fontsize=14, fontweight="bold", y=0.98)
    plt.tight_layout()
    fig3_path = os.path.join(fig_dir, "transit_accessibility_distribution.png")
    fig.savefig(fig3_path, dpi=300)
    plt.close(fig)
    print(f"   -> 저장 완료: {fig3_path}")

    # ----------------------------------------------------
    # Figure 4: 주차 수용용량 vs 점포 수 산점도 및 주차 수급 격차 분석
    # ----------------------------------------------------
    print("[4/4] parking_capacity_vs_stores.png 생성 중...")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

    # 산점도 (ax1)
    district_palette = {
        "중구": "#E63946", "달서구": "#1D3557", "수성구": "#457B9D",
        "북구": "#2A9D8F", "동구": "#E76F51", "서구": "#A8DADC",
        "남구": "#F4A261", "달성군": "#6D6875", "군위군": "#B5838D"
    }

    for sgg, grp in df_dong.groupby("signgu_nm"):
        c = district_palette.get(sgg, "#333333")
        ax1.scatter(
            grp["total_stores"], grp["dong_total_parking_capacity"],
            s=grp["pop_total"] / 400 + 20,
            c=c, alpha=0.75, edgecolors="white", linewidths=0.7,
            label=sgg
        )

    # 추세선
    z = np.polyfit(df_dong["total_stores"], df_dong["dong_total_parking_capacity"], 1)
    p = np.poly1d(z)
    x_vals = np.linspace(df_dong["total_stores"].min(), df_dong["total_stores"].max(), 100)
    ax1.plot(x_vals, p(x_vals), "k--", alpha=0.6, linewidth=1.2, label=f"선형 추세선 (기울기: {z[0]:.2f})")

    # 주요 특이치 레이블링
    outliers = ["성내1동", "대신동", "성내2동", "신당동", "다사읍", "범어동", "두류1.2동"]
    for _, row in df_dong.iterrows():
        short_nm = row["adm_nm"].split()[-1]
        if short_nm in outliers:
            ax1.annotate(
                short_nm,
                xy=(row["total_stores"], row["dong_total_parking_capacity"]),
                xytext=(5, 5),
                textcoords="offset points",
                fontsize=8.5,
                fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="yellow", alpha=0.4, edgecolor="#888", lw=0.5)
            )

    ax1.set_title("행정동별 점포 수 대비 총 부설주차면수 (버블 크기: 인구수)", fontsize=12, fontweight="bold")
    ax1.set_xlabel("행정동 총 점포 수 (개소)", fontsize=10)
    ax1.set_ylabel("행정동 총 부설주차면수 (면)", fontsize=10)
    ax1.legend(loc="upper left", fontsize=8, frameon=True, ncol=2)
    ax1.grid(True, linestyle="--", alpha=0.3)

    # 구별 점포당 주차면수 및 인구천명당 주차면수 (ax2)
    dist_parking = df_dong.groupby("signgu_nm").agg(
        total_stores=("total_stores", "sum"),
        total_cap=("dong_total_parking_capacity", "sum"),
        total_pop=("pop_total", "sum")
    ).reindex(district_order)

    dist_parking["cap_per_store"] = dist_parking["total_cap"] / dist_parking["total_stores"]
    dist_parking["cap_per_1000_pop"] = dist_parking["total_cap"] / (dist_parking["total_pop"] / 1000)

    y = np.arange(len(district_order))
    h = 0.35
    ax2.barh(y - h/2, dist_parking["cap_per_store"], height=h, color="#457B9D", label="점포당 주차면수 (면/점포)")
    ax2.barh(y + h/2, dist_parking["cap_per_1000_pop"] / 50, height=h, color="#E76F51", label="인구천명당 주차면수 (50면 단위)")

    ax2.set_yticks(y)
    ax2.set_yticklabels(district_order, fontsize=9.5)
    ax2.invert_yaxis()
    ax2.set_title("대구 자치구·군별 주차 공급 지표 비교", fontsize=12, fontweight="bold")
    ax2.set_xlabel("지표 수치", fontsize=10)
    ax2.legend(loc="lower right", fontsize=9)
    ax2.grid(axis="x", linestyle="--", alpha=0.3)

    fig.suptitle("대구 상권 부설주차 수용용량 공급 구조 및 상업 밀도 대비 수급 분석", fontsize=14, fontweight="bold", y=0.98)
    plt.tight_layout()
    fig4_path = os.path.join(fig_dir, "parking_capacity_vs_stores.png")
    fig.savefig(fig4_path, dpi=300)
    plt.close(fig)
    print(f"   -> 저장 완료: {fig4_path}")

    print("\n[COMPLETE] 4개 시각화 아티팩트가 모두 정상 생성되었습니다.")

if __name__ == "__main__":
    generate_visualizations()
