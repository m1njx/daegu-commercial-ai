# 데이터 디렉터리 안내서 (Data Catalog & Guide)

**팀명**: 말괄량이코물이  
**프로젝트**: 대구 소상공인 AI 상권·창업 입지 추천 서비스  
**공모전**: 2026 AI Blockchain Challenge in Daegu  

본 문서는 `data/` 디렉터리에 포함된 전처리 피처마트, 공간 지오메트리, 대중교통 인프라 데이터의 구조와 컬럼 명세, 처리 기준을 설명합니다.

---

## 1. 디렉터리 구성

```
data/
├── processed/                         # 모델 서빙 및 추천에 즉각 활용되는 정제 피처마트
│   ├── feature_mart/                  # 행정동 단위 상권·인구·공간 피처마트
│   │   ├── commercial_feature_mart_dong.parquet (64KB, 150행 × 47열)
│   │   ├── commercial_feature_mart_dong.csv     (42KB, 150행 × 47열)
│   │   ├── commercial_feature_mart_dong_category.parquet (94KB, 1,454행 × 29열)
│   │   ├── commercial_feature_mart_dong_category.csv     (287KB, 1,454행 × 29열)
│   │   └── store_spatial_features.parquet       (8.6MB, 118,357행 점포 공간통계)
│   ├── geojson/                       # 행정동 경계 지도 데이터
│   │   └── 대구_행정동_경계_20230701.geojson    (1.5MB, 150개 동 폴리곤 WGS84)
│   ├── transit/                       # 도시철도 및 시내버스 대중교통 인프라 데이터
│   │   ├── bus/                       # 시내버스 동 단위 및 정류소 피처
│   │   │   ├── daegu_bus_dong_features.parquet  (18KB, 150행 × 11열)
│   │   │   ├── daegu_bus_dong_features.csv      (15KB, 150행 × 11열)
│   │   │   └── daegu_bus_stops_processed.parquet(316KB, 3,981개 정류소 좌표)
│   │   └── 대구도시철도_역별_위경도좌표.csv    (3.1KB, 94개 역사 좌표)
│   └── recommendation_scores.parquet  (214KB, 사전 계산 벤치마크 점수)
│
└── raw/bus/                           # Phase 8 자동화 테스트 재현용 공공 버스 원천 데이터
    ├── 대구광역시_시내버스 정류소 위치정보_20250903.csv (482KB, 3,981개 정류소)
    └── 대구광역시_시내버스  정류소별 월별 이용자수_20260731/
        └── 시내버스 정류소별 월별 이용자수(2026-01~07).csv (1.2MB, 2026년 실측치)
```

---

## 2. 주요 데이터셋 상세 명세

### A. 행정동 종합 피처마트 (`commercial_feature_mart_dong.parquet`)
대구광역시 150개 행정동을 단일 행(Row)으로 집계한 최상위 의사결정 피처마트입니다.
- **주요 컬럼**:
  - `adm_cd2`: 행정동 10자리 고유 코드 (Key)
  - `adm_nm`: 행정동 공식 명칭 (예: `대구광역시 동구 신암4동`)
  - `total_pop`: 행정동 총 거주인구
  - `pop_2030`: 20~39세 청년 소비층 인구수
  - `ratio_2030`: 전체 인구 대비 2030 인구 비율
  - `total_stores`: 동 관내 전체 소상공인 점포 수
  - `dong_station_count`: 동 관내 도시철도 역사 수
  - `nearest_station_dist_m`: 동 중심점으로부터 가장 가까운 도시철도역까지의 거리(미터)
  - `subway_ridership_weight`: 도시철도 역세권 가중 접근성 점수
  - `parking_spaces`: 행정동 등록 부설주차장 총 주차면수

### B. 시내버스 행정동 피처 (`daegu_bus_dong_features.parquet`)
대구시 3,981개 정류소 및 2026년 1~7월 212일간의 실제 승하차 데이터를 공간 결합한 피처입니다.
- **주요 컬럼**:
  - `adm_cd2`: 행정동 고유 코드 (150개 동 100% 매핑)
  - `dong_bus_stop_count`: 행정동 관내 정류소 개수 (최소 1개 이상, 결측 0)
  - `dong_daily_bus_boarding`: 일평균 승차 인원 합계
  - `dong_daily_bus_alighting`: 일평균 하차 인원 합계
  - `dong_daily_bus_total`: 일평균 총 승하차 인원 합계
  - `dong_bus_stop_density`: 단위 면적당 정류소 밀도
  - `avg_dist_to_bus_m`: 동내 상가 점포들로부터 최인접 정류소까지의 평균 거리(미터)
  - `ratio_stores_in_bus_300m`: 정류소 반경 300m 도보권 내에 위치한 점포 비율

이용량 원천은 정류소명만 제공하므로, 같은 이름의 표지판을 300m 근접 공간 군집으로 구분합니다. 원거리 동명이인은 별도 군집으로 분리하고 이름 단위 이용량을 군집 간, 이어 군집 내 표지판 간 균등 배분합니다. 이 가정은 매칭된 원천 총량을 보존하지만 개별 표지판의 직접 관측값을 뜻하지 않습니다.

### C. 행정동 경계 지도 (`대구_행정동_경계_20230701.geojson`)
- 2023년 7월 1일 대구광역시에 공식 편입된 군위군 8개 읍·면(군위읍, 소보면, 효령면, 부계면, 우보면, 의흥면, 산성면, 삼국유사면)을 완벽히 포함하는 최신 150개 행정동 공간 경계 데이터입니다.
- 좌표계: WGS84 (EPSG:4326), 유효 폴리곤 무결성 검증 완료.

---

## 3. 공간 좌표 처리 및 무결성 검증

1. **투영 좌표계 변환 (CRS Management)**:
   - 미터 단위의 정확한 거리 및 반경 버퍼(300m) 계산을 위해 대한민국 국가표준 평면직각좌표계인 `EPSG:5179` (UTM-K)로 투영 변환하여 공간 조인을 수행했습니다.
   - 웹 시각화 및 Folium 맵 표출 시에는 국제 표준 경위도 좌표계인 `EPSG:4326` (WGS84)로 자동 변환하여 오차를 방지했습니다.
2. **결측치 및 이상치 제로화**:
   - 150개 행정동 전수에 걸쳐 NaN, Null, Infinite 수치가 단 1건도 존재하지 않음을 확인했습니다.

---
**팀 말괄량이코물이 | 2026 AI Blockchain Challenge in Daegu**
