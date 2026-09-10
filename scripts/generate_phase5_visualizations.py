#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/generate_phase5_visualizations.py

Phase 5: 상권 입지 추천 모델링 결과 시각화 아티팩트 생성 스크립트
1) recommendation_suitability_map.png & .html: 행정동별 종합 적합도 지도 (PNG + Folium 인터랙티브)
2) top10_rankings_by_industry.png: 5대 핵심 업종별 Top 10 추천 순위 및 점수 비교
3) component_score_breakdown.png: 상위 5대 추천 지역의 6대 컴포넌트 점수 프로파일
4) competition_vs_suitability.png: 경쟁 기회도 vs 종합 적합도 산점도
5) accessibility_vs_suitability.png: 대중교통 접근성 vs 종합 적합도 산점도
6) parking_vs_suitability.png: 주차 공급 지표 vs 종합 적합도 산점도
"""

import os
import sys
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd
import geopandas as gpd
import folium

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
fig_dir = os.path.join(base_dir, "reports/figures")
os.makedirs(fig_dir, exist_ok=True)

def setup_matplotlib():
    plt.rcParams["font.family"] = "AppleGothic"
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 300

def generate_visualizations():
    setup_matplotlib()
    print("[VISUALIZATION] 데이터셋 로드 중...")
    
    rec_path = os.path.join(base_dir, "data/processed/recommendation_scores.parquet")
    geojson_path = os.path.join(base_dir, "data/processed/geojson/대구_행정동_경계_20230701.geojson")
    transit_path = os.path.join(base_dir, "data/processed/transit/대구도시철도_역별_위경도좌표.csv")
    
    df_rec = pd.read_parquet(rec_path)
    gdf_dong = gpd.read_file(geojson_path)
    gdf_dong["adm_cd2"] = gdf_dong["adm_cd2"].astype(str)
    df_transit = pd.read_csv(transit_path, encoding="utf-8-sig")
    
    # 대표 케이스: 카페 (2030 타깃)
    cafe_rec = df_rec[df_rec["query_industry"] == "카페"].copy()
    gdf_cafe = gdf_dong.merge(cafe_rec, on="adm_cd2", how="left")
    
    # ----------------------------------------------------
    # 1. 행정동별 입지 적합도 지도 (PNG + Folium HTML)
    # ----------------------------------------------------
    print("[1/6] recommendation_suitability_map.png 생성 중...")
    fig, ax = plt.subplots(figsize=(12, 11))
    
    gdf_cafe.plot(
        column="total_score",
        ax=ax,
        cmap="RdYlGn",
        legend=True,
        legend_kwds={
            "label": "카페 창업 입지 적합도 점수 (0 ~ 100점)",
            "orientation": "horizontal",
            "shrink": 0.5,
            "pad": 0.02
        },
        edgecolor="#666666",
        linewidth=0.4,
        vmin=10, vmax=90
    )
    
    # 지하철역 오버레이
    ax.scatter(
        df_transit["lon"], df_transit["lat"],
        c="#111111", s=14, alpha=0.6, edgecolors="white", linewidths=0.4,
        label="도시철도 역사 (94개소)", zorder=4
    )
    
    # Top 5 추천 행정동 레이블링
    top5_dongs = cafe_rec.sort_values("rank").head(5)
    for _, row in top5_dongs.iterrows():
        match_geom = gdf_cafe[gdf_cafe["adm_cd2"] == row["adm_cd2"]]
        if not match_geom.empty:
            pt = match_geom.iloc[0].geometry.centroid
            short_nm = row["adm_nm"].split()[-1]
            ax.annotate(
                f"{row['rank']}위: {short_nm}\n({row['total_score']}점)",
                xy=(pt.x, pt.y),
                xytext=(5, 5),
                textcoords="offset points",
                fontsize=8.5,
                fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.25", facecolor="#FFFDE7", alpha=0.9, edgecolor="#E65100", lw=1.2),
                arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0.1", color="#E65100", lw=0.8)
            )
            
    ax.set_title("대구광역시 행정동별 '2030 청년 타깃 카페' 창업 입지 적합도 공간 분포", fontsize=14, fontweight="bold", pad=12)
    ax.set_xlabel("경도 (WGS84)", fontsize=10)
    ax.set_ylabel("위도 (WGS84)", fontsize=10)
    ax.legend(loc="lower left", frameon=True, facecolor="white", fontsize=9)
    ax.grid(True, linestyle="--", alpha=0.3)
    plt.tight_layout()
    fig1_png = os.path.join(fig_dir, "recommendation_suitability_map.png")
    fig.savefig(fig1_png, dpi=300)
    plt.close(fig)
    print(f"   -> 저장 완료: {fig1_png}")
    
    # Folium 인터랙티브 지도 생성
    print("   -> recommendation_suitability_map.html 생성 중...")
    m = folium.Map(location=[35.8714, 128.6014], zoom_start=11, tiles="CartoDB positron")
    
    # 코로플레스 레이어
    folium.Choropleth(
        geo_data=geojson_path,
        name="입지 적합도",
        data=cafe_rec,
        columns=["adm_cd2", "total_score"],
        key_on="feature.properties.adm_cd2",
        fill_color="YlGnBu",
        fill_opacity=0.7,
        line_opacity=0.3,
        legend_name="추천 적합도 점수 (0~100점)"
    ).add_to(m)
    
    # Top 10 마커 추가
    for _, row in cafe_rec.head(10).iterrows():
        match_geom = gdf_cafe[gdf_cafe["adm_cd2"] == row["adm_cd2"]]
        if not match_geom.empty:
            pt = match_geom.iloc[0].geometry.centroid
            short_nm = row["adm_nm"].split()[-1]
            popup_text = (
                f"<b>{row['rank']}위: {short_nm}</b><br>"
                f"종합점수: {row['total_score']}점<br>"
                f"배후수요: {row['demand_score']}점 | 타깃적합: {row['target_fit_score']}점<br>"
                f"경쟁환경: {row['competition_score']}점 | 교통접근: {row['accessibility_score']}점<br>"
                f"주차공급: {row['parking_score']}점 | 업종특화: {row['industry_fit_score']}점"
            )
            folium.Marker(
                location=[pt.y, pt.x],
                popup=popup_text,
                tooltip=f"{row['rank']}위: {short_nm} ({row['total_score']}점)",
                icon=folium.Icon(color="red" if row["rank"] <= 3 else "blue", icon="star" if row["rank"] <= 3 else "info-sign")
            ).add_to(m)
            
    fig1_html = os.path.join(fig_dir, "recommendation_suitability_map.html")
    m.save(fig1_html)
    print(f"   -> 저장 완료: {fig1_html}")

    # ----------------------------------------------------
    # 2. 업종별 Top 10 랭킹 및 점수 비교
    # ----------------------------------------------------
    print("[2/6] top10_rankings_by_industry.png 생성 중...")
    target_industries = ["카페", "한식", "미용실", "학원", "종합소매"]
    fig, axes = plt.subplots(1, 5, figsize=(20, 8), sharey=True)
    
    palette = ["#2A9D8F", "#E76F51", "#F4A261", "#457B9D", "#1D3557"]
    
    for i, ind in enumerate(target_industries):
        ax = axes[i]
        sub_df = df_rec[df_rec["query_industry"] == ind].sort_values("rank").head(10)
        short_names = [n.split()[-1] for n in sub_df["adm_nm"]]
        
        bars = ax.barh(short_names[::-1], sub_df["total_score"].values[::-1], color=palette[i], alpha=0.85, height=0.65)
        ax.set_title(f"{ind} Top 10", fontsize=12, fontweight="bold")
        ax.set_xlabel("적합도 점수", fontsize=10)
        ax.set_xlim(50, 90)
        ax.grid(axis="x", linestyle="--", alpha=0.3)
        
        for bar in bars:
            w = bar.get_width()
            ax.text(w + 0.5, bar.get_y() + bar.get_height()/2, f"{w:.1f}", va="center", fontsize=8.5, fontweight="bold")
            
    fig.suptitle("대구광역시 5대 핵심 업종별 추천 순위 및 종합 적합도 점수 Top 10", fontsize=15, fontweight="bold", y=0.98)
    plt.tight_layout()
    fig2_png = os.path.join(fig_dir, "top10_rankings_by_industry.png")
    fig.savefig(fig2_png, dpi=300)
    plt.close(fig)
    print(f"   -> 저장 완료: {fig2_png}")

    # ----------------------------------------------------
    # 3. 상위 5대 추천 행정동의 6대 컴포넌트 점수 프로파일
    # ----------------------------------------------------
    print("[3/6] component_score_breakdown.png 생성 중...")
    fig, ax = plt.subplots(figsize=(14, 7))
    
    top5 = cafe_rec.sort_values("rank").head(5)
    components = [
        ("demand_score", "배후수요 (30%)"),
        ("target_fit_score", "타깃고객 (20%)"),
        ("competition_score", "경쟁환경 (15%)"),
        ("accessibility_score", "교통접근성 (15%)"),
        ("parking_score", "주차공급 (10%)"),
        ("industry_fit_score", "업종특화 (10%)"),
    ]
    
    dong_labels = [f"{r['rank']}위: {r['adm_nm'].split()[-1]}" for _, r in top5.iterrows()]
    x = np.arange(len(dong_labels))
    width = 0.13
    comp_colors = ["#457B9D", "#E76F51", "#2A9D8F", "#E63946", "#F4A261", "#8D99AE"]
    
    for j, (col, label) in enumerate(components):
        vals = top5[col].values
        rects = ax.bar(x + (j - 2.5) * width, vals, width, label=label, color=comp_colors[j], alpha=0.9)
        
    ax.set_title("카페 창업 추천 상위 5개 지역의 6대 컴포넌트 점수 비교", fontsize=13, fontweight="bold", pad=12)
    ax.set_ylabel("컴포넌트 점수 (0 ~ 100점)", fontsize=10)
    ax.set_xticks(x)
    ax.set_xticklabels(dong_labels, fontsize=10.5, fontweight="bold")
    ax.set_ylim(0, 110)
    ax.legend(loc="upper right", frameon=True, fontsize=9, ncol=3)
    ax.grid(axis="y", linestyle="--", alpha=0.3)
    
    plt.tight_layout()
    fig3_png = os.path.join(fig_dir, "component_score_breakdown.png")
    fig.savefig(fig3_png, dpi=300)
    plt.close(fig)
    print(f"   -> 저장 완료: {fig3_png}")

    # ----------------------------------------------------
    # 4. 경쟁 환경 vs 종합 적합도 산점도
    # ----------------------------------------------------
    print("[4/6] competition_vs_suitability.png 생성 중...")
    fig, ax = plt.subplots(figsize=(10, 7))
    
    scatter = ax.scatter(
        cafe_rec["competition_score"], cafe_rec["total_score"],
        s=cafe_rec["pop_total"] / 300 + 20,
        c=cafe_rec["demand_score"], cmap="viridis",
        alpha=0.8, edgecolors="white", linewidth=0.7
    )
    cb = fig.colorbar(scatter, ax=ax, shrink=0.8)
    cb.set_label("배후 수요 점수 (Demand Score)", fontsize=9.5)
    
    # 주요 상위권 레이블링
    for _, row in cafe_rec.head(8).iterrows():
        short_nm = row["adm_nm"].split()[-1]
        ax.annotate(
            f"{row['rank']}위 {short_nm}",
            xy=(row["competition_score"], row["total_score"]),
            xytext=(4, 4),
            textcoords="offset points",
            fontsize=8.5,
            fontweight="bold"
        )
        
    ax.set_title("카페 창업: 경쟁 환경 점수(기회도) vs 종합 입지 적합도 (점 크기: 총인구)", fontsize=12, fontweight="bold")
    ax.set_xlabel("경쟁 환경 점수 (높을수록 미포화 성장기회)", fontsize=10)
    ax.set_ylabel("종합 입지 적합도 (Total Score)", fontsize=10)
    ax.grid(True, linestyle="--", alpha=0.3)
    plt.tight_layout()
    fig4_png = os.path.join(fig_dir, "competition_vs_suitability.png")
    fig.savefig(fig4_png, dpi=300)
    plt.close(fig)
    print(f"   -> 저장 완료: {fig4_png}")

    # ----------------------------------------------------
    # 5. 대중교통 접근성 vs 종합 적합도 산점도
    # ----------------------------------------------------
    print("[5/6] accessibility_vs_suitability.png 생성 중...")
    fig, ax = plt.subplots(figsize=(10, 7))
    
    scatter = ax.scatter(
        cafe_rec["accessibility_score"], cafe_rec["total_score"],
        s=cafe_rec["target_pop"] / 200 + 20,
        c=cafe_rec["target_fit_score"], cmap="plasma",
        alpha=0.8, edgecolors="white", linewidth=0.7
    )
    cb = fig.colorbar(scatter, ax=ax, shrink=0.8)
    cb.set_label("타깃 적합도 점수 (Target Fit)", fontsize=9.5)
    
    for _, row in cafe_rec.head(8).iterrows():
        short_nm = row["adm_nm"].split()[-1]
        ax.annotate(
            f"{row['rank']}위 {short_nm}",
            xy=(row["accessibility_score"], row["total_score"]),
            xytext=(4, 4),
            textcoords="offset points",
            fontsize=8.5,
            fontweight="bold"
        )
        
    ax.set_title("카페 창업: 대중교통 접근성 점수 vs 종합 입지 적합도 (점 크기: 2030인구)", fontsize=12, fontweight="bold")
    ax.set_xlabel("대중교통 접근성 점수 (Accessibility Score)", fontsize=10)
    ax.set_ylabel("종합 입지 적합도 (Total Score)", fontsize=10)
    ax.grid(True, linestyle="--", alpha=0.3)
    plt.tight_layout()
    fig5_png = os.path.join(fig_dir, "accessibility_vs_suitability.png")
    fig.savefig(fig5_png, dpi=300)
    plt.close(fig)
    print(f"   -> 저장 완료: {fig5_png}")

    # ----------------------------------------------------
    # 6. 주차 공급 vs 종합 적합도 산점도
    # ----------------------------------------------------
    print("[6/6] parking_vs_suitability.png 생성 중...")
    fig, ax = plt.subplots(figsize=(10, 7))
    
    scatter = ax.scatter(
        cafe_rec["parking_score"], cafe_rec["total_score"],
        s=cafe_rec["cat_store_count"] * 2 + 30,
        c=cafe_rec["industry_fit_score"], cmap="coolwarm",
        alpha=0.8, edgecolors="white", linewidth=0.7
    )
    cb = fig.colorbar(scatter, ax=ax, shrink=0.8)
    cb.set_label("업종 특화도 점수 (LQ Score)", fontsize=9.5)
    
    for _, row in cafe_rec.head(8).iterrows():
        short_nm = row["adm_nm"].split()[-1]
        ax.annotate(
            f"{row['rank']}위 {short_nm}",
            xy=(row["parking_score"], row["total_score"]),
            xytext=(4, 4),
            textcoords="offset points",
            fontsize=8.5,
            fontweight="bold"
        )
        
    ax.set_title("카페 창업: 부설주차 공급 지표 vs 종합 입지 적합도 (점 크기: 동내 카페수)", fontsize=12, fontweight="bold")
    ax.set_xlabel("주차 공급 점수 (부설주차장 수용능력 proxy)", fontsize=10)
    ax.set_ylabel("종합 입지 적합도 (Total Score)", fontsize=10)
    ax.grid(True, linestyle="--", alpha=0.3)
    plt.tight_layout()
    fig6_png = os.path.join(fig_dir, "parking_vs_suitability.png")
    fig.savefig(fig6_png, dpi=300)
    plt.close(fig)
    print(f"   -> 저장 완료: {fig6_png}")

    print("\n[COMPLETE] 6개 시각화 아티팩트가 모두 정상 생성되었습니다.")

if __name__ == "__main__":
    generate_visualizations()
