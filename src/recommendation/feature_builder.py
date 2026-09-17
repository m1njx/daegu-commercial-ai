# -*- coding: utf-8 -*-
"""
src/recommendation/feature_builder.py

행정동별 업종 및 타깃 고객층 기반 추천 입력 Feature Matrix 생성 모듈
- 150개 행정동 전수 대상
- 대분류(10종), 중분류(75종), 주요 일상 업종(카페, 음식점, 미용실, 학원, 소매업) 지원
- 연령대별(10대, 20대, 30대, 40대, 50대, 60대이상, 2030, 4050) 타깃 고객 맞춤 계산
"""

import pandas as pd
import numpy as np
from scipy.spatial import cKDTree
from typing import Optional, Dict, Any, Tuple

# 업종 검색어 및 표준 매핑 사전
INDUSTRY_ALIASES = {
    "카페": {"level": "mcls", "target": ["비알코올"], "label": "카페 (비알코올 음료점)"},
    "커피": {"level": "mcls", "target": ["비알코올"], "label": "카페 (비알코올 음료점)"},
    "음식점": {"level": "lcls", "target": ["음식"], "label": "음식점 (요식업 전체)"},
    "외식업": {"level": "lcls", "target": ["음식"], "label": "음식점 (요식업 전체)"},
    "한식": {"level": "mcls", "target": ["한식"], "label": "한식 음식점"},
    "미용실": {"level": "mcls", "target": ["이용·미용"], "label": "미용실 (이용·미용)"},
    "헤어샵": {"level": "mcls", "target": ["이용·미용"], "label": "미용실 (이용·미용)"},
    "학원": {"level": "mcls", "target": ["일반 교육", "기타 교육"], "label": "학원 (일반·기타 교육)"},
    "교육": {"level": "lcls", "target": ["교육"], "label": "교육 서비스업 전체"},
    "소매업": {"level": "lcls", "target": ["소매"], "label": "소매업 전체"},
    "소매": {"level": "lcls", "target": ["소매"], "label": "소매업 전체"},
    "종합소매": {"level": "mcls", "target": ["종합 소매"], "label": "종합 소매점"},
    "숙박": {"level": "lcls", "target": ["숙박"], "label": "숙박업 전체"},
    "예술·스포츠": {"level": "lcls", "target": ["예술·스포츠"], "label": "예술·스포츠 서비스업"},
}

def resolve_industry_filter(query: str, df_store: pd.DataFrame) -> Tuple[pd.Series, str]:
    """
    사용자의 업종 검색어를 바탕으로 df_store 필터링 불리언 시리즈와 표준 라벨을 반환합니다.
    """
    if not isinstance(query, str):
        raise ValueError("업종 검색어는 문자열이어야 합니다.")
    clean_query = query.strip()
    if not clean_query:
        raise ValueError("업종 검색어를 입력해 주세요.")
    if len(clean_query) > 50:
        raise ValueError("업종 검색어는 50자 이내로 입력해 주세요.")
    
    # 1. 사전 정의된 별칭 매핑 확인
    if clean_query in INDUSTRY_ALIASES:
        meta = INDUSTRY_ALIASES[clean_query]
        if meta["level"] == "lcls":
            mask = df_store["indsLclsNm"].isin(meta["target"])
        else:
            mask = df_store["indsMclsNm"].isin(meta["target"])
        return mask, meta["label"]
    
    # 2. 대분류 exact 매칭 확인
    lcls_unique = set(df_store["indsLclsNm"].unique())
    if clean_query in lcls_unique:
        return (df_store["indsLclsNm"] == clean_query), f"{clean_query} (업종대분류)"
    
    # 3. 중분류 exact 매칭 확인
    mcls_unique = set(df_store["indsMclsNm"].unique())
    if clean_query in mcls_unique:
        return (df_store["indsMclsNm"] == clean_query), f"{clean_query} (업종중분류)"
    
    # 4. 부분 일치 검색
    partial_mcls = [m for m in mcls_unique if clean_query in m]
    if partial_mcls:
        mask = df_store["indsMclsNm"].isin(partial_mcls)
        return mask, f"{', '.join(partial_mcls[:2])} 관련 업종"
        
    partial_lcls = [l for l in lcls_unique if clean_query in l]
    if partial_lcls:
        mask = df_store["indsLclsNm"].isin(partial_lcls)
        return mask, f"{partial_lcls[0]} 관련 업종"
        
    raise ValueError("지원하지 않는 업종입니다. 가능한 예시: 카페, 음식점, 일식, 중식, 미용실, 학원, 소매업 등")

def resolve_target_demographic(target_age: Optional[str], df_dong: pd.DataFrame) -> Tuple[pd.Series, pd.Series, str]:
    """
    선택된 타깃 연령대에 따라 해당 행정동의 타깃 인구수, 인구비율, 라벨을 반환합니다.
    """
    if not target_age or str(target_age).lower() in ["all", "none", "전체"]:
        return df_dong["pop_total"].copy(), pd.Series(1.0, index=df_dong.index), "전체 인구"
    
    tag = str(target_age).strip().lower()
    
    if tag in ["10s", "10대", "under20", "청소년"]:
        pop = df_dong["pop_under20"].copy()
        ratio = (pop / df_dong["pop_total"]).round(4)
        return pop, ratio, "10대 이하 (0~19세)"
    elif tag in ["20s", "20대"]:
        pop = df_dong["pop_20s"].copy()
        ratio = (pop / df_dong["pop_total"]).round(4)
        return pop, ratio, "20대 청년층"
    elif tag in ["30s", "30대"]:
        pop = df_dong["pop_30s"].copy()
        ratio = (pop / df_dong["pop_total"]).round(4)
        return pop, ratio, "30대 직장인/청장년층"
    elif tag in ["2030", "20-30", "20-39", "청년"]:
        pop = (df_dong["pop_20s"] + df_dong["pop_30s"]).copy()
        ratio = (pop / df_dong["pop_total"]).round(4)
        return pop, ratio, "2030 청년 소비층 (20~39세)"
    elif tag in ["40s", "40대"]:
        pop = df_dong["pop_40s"].copy()
        ratio = (pop / df_dong["pop_total"]).round(4)
        return pop, ratio, "40대 중년층"
    elif tag in ["50s", "50대"]:
        pop = df_dong["pop_50s"].copy()
        ratio = (pop / df_dong["pop_total"]).round(4)
        return pop, ratio, "50대 장년층"
    elif tag in ["4050", "40-50", "40-59", "중장년"]:
        pop = (df_dong["pop_40s"] + df_dong["pop_50s"]).copy()
        ratio = (pop / df_dong["pop_total"]).round(4)
        return pop, ratio, "4050 중장년 구매력층 (40~59세)"
    elif tag in ["60plus", "60대", "60대이상", "고령", "시니어"]:
        pop = df_dong["pop_60plus"].copy()
        ratio = (pop / df_dong["pop_total"]).round(4)
        return pop, ratio, "60대 이상 시니어층"
    else:
        # 기본값: 2030 청년층
        pop = (df_dong["pop_20s"] + df_dong["pop_30s"]).copy()
        ratio = (pop / df_dong["pop_total"]).round(4)
        return pop, ratio, "2030 청년 소비층 (기본값)"


def calculate_selected_category_competition(matched_stores: pd.DataFrame) -> pd.Series:
    """Return each selected store's nearby competitors within 300 metres.

    The competitor universe is exactly the store set resolved from the user's
    industry selection.  The focal store itself is excluded.  This avoids the
    former mismatch where a broad or multi-middle-category selection was
    displayed as "same-industry competition" while the stored value counted
    only each focal store's own middle category.
    """
    if matched_stores.empty:
        return pd.Series(dtype="int64", index=matched_stores.index)
    required = {"x_utm", "y_utm"}
    missing = sorted(required.difference(matched_stores.columns))
    if missing:
        raise ValueError(f"경쟁점포 계산에 필요한 좌표 컬럼이 없습니다: {missing}")
    coords = matched_stores[["x_utm", "y_utm"]].to_numpy(dtype=float)
    if not np.isfinite(coords).all():
        raise ValueError("경쟁점포 계산 좌표에 결측치 또는 무한값이 있습니다.")
    counts = cKDTree(coords).query_ball_point(coords, r=300.0, return_length=True) - 1
    return pd.Series(counts.astype(int), index=matched_stores.index)

def build_dong_industry_features(
    industry_query: str,
    target_age: Optional[str],
    df_dong: pd.DataFrame,
    df_store: pd.DataFrame,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    주어진 업종과 타깃 연령대에 맞춰 150개 행정동의 통합 피처 행렬을 동적으로 구축합니다.
    """
    # 0. 데이터 복사 및 공백 정제
    df_s = df_store.copy()
    df_s["indsMclsNm"] = df_s["indsMclsNm"].astype(str).str.strip()
    df_s["indsLclsNm"] = df_s["indsLclsNm"].astype(str).str.strip()
    
    # 1. 업종 필터 매핑
    ind_mask, ind_label = resolve_industry_filter(industry_query, df_s)
    matched_stores = df_s[ind_mask].copy()
    matched_stores["selected_category_competitor_count_300m"] = (
        calculate_selected_category_competition(matched_stores)
    )
    city_industry_total = len(matched_stores)
    city_store_total = len(df_s)
    
    if city_industry_total == 0:
        raise ValueError(f"해당 업종 점포가 대구시 데이터에 0건입니다: '{industry_query}'")
        
    # 2. 타깃 인구 필터 매핑
    target_pop_series, target_ratio_series, target_label = resolve_target_demographic(target_age, df_dong)
    
    # 3. 행정동 기준 업종 집계
    if len(matched_stores) > 0:
        dong_cat_stats = matched_stores.groupby("adm_cd2").agg(
            cat_store_count=("bizesId", "count"),
            cat_avg_subway_dist=("nearest_subway_dist_m", "mean"),
            cat_ratio_subway=("is_subway_zone", "mean"),
            cat_avg_parking_300m=("parking_capacity_300m", "mean"),
            cat_avg_comp_300m=("selected_category_competitor_count_300m", "mean")
        ).reset_index()
    else:
        dong_cat_stats = pd.DataFrame(columns=["adm_cd2", "cat_store_count", "cat_avg_subway_dist",
                                               "cat_ratio_subway", "cat_avg_parking_300m", "cat_avg_comp_300m"])
        
    # 4. 150개 행정동 기본 마트와 결합
    features = df_dong[[
        "adm_cd2", "adm_nm", "signgu_cd", "signgu_nm", "area_km2",
        "pop_total", "pop_density", "total_stores", "store_density_km2",
        "avg_dist_to_subway_m", "ratio_stores_in_subway_zone", "dong_station_count", "dong_daily_ridership",
        "dong_parking_lot_count", "dong_total_parking_capacity", "parking_capacity_per_store", "avg_parking_capacity_300m",
        "category_entropy"
    ]].copy()
    
    features = features.merge(dong_cat_stats, on="adm_cd2", how="left")
    
    # 결측치 정제 (해당 동에 해당 업종 점포가 없는 경우 행정동 기본값 또는 0 적용)
    features["cat_store_count"] = features["cat_store_count"].fillna(0).astype(int)
    features["cat_avg_subway_dist"] = features["cat_avg_subway_dist"].fillna(features["avg_dist_to_subway_m"]).round(1)
    features["cat_ratio_subway"] = features["cat_ratio_subway"].fillna(features["ratio_stores_in_subway_zone"]).round(4)
    features["cat_avg_parking_300m"] = features["cat_avg_parking_300m"].fillna(features["avg_parking_capacity_300m"]).round(1)
    features["cat_avg_comp_300m"] = features["cat_avg_comp_300m"].fillna(0.0).round(1)
    
    # 5. 타깃 인구 결합
    features["target_pop"] = target_pop_series.values
    features["target_ratio"] = target_ratio_series.values
    
    # 6. 파생 특화 지표 계산
    # LQ (Location Quotient) = (동내 업종점포수 / 동내 총점포수) / (시전체 업종점포수 / 시전체 총점포수)
    city_share = city_industry_total / city_store_total
    raw_store_share_in_dong = np.where(
        features["total_stores"] > 0,
        features["cat_store_count"] / features["total_stores"],
        0.0
    )
    features["store_share_in_dong"] = np.round(raw_store_share_in_dong, 4)
    features["location_quotient"] = np.where(
        features["total_stores"] > 0,
        np.round(raw_store_share_in_dong / city_share, 3),
        0.0
    )
    
    # 수요 대비 경쟁 여유도 (점포당 배후 인구)
    # 점포수가 0인 경우를 고려하여 +1 smoothing 적용
    features["pop_per_store"] = (features["pop_total"] / (features["cat_store_count"] + 1)).round(1)
    features["target_pop_per_store"] = (features["target_pop"] / (features["cat_store_count"] + 1)).round(1)
    
    metadata = {
        "industry_query": industry_query,
        "industry_label": ind_label,
        "competition_scope": ind_label,
        "competition_radius_m": 300,
        "city_industry_total": city_industry_total,
        "target_age_query": target_age,
        "target_demographic_label": target_label,
        "total_dongs": len(features),
    }
    
    return features, metadata
