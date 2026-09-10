# 프로젝트 디렉터리 및 아키텍처 가이드 (Project Structure)

**팀명**: 말괄량이코물이  
**프로젝트**: 대구 소상공인 AI 상권·창업 입지 추천 서비스  
**공모전**: 2026 AI Blockchain Challenge in Daegu  

---

## 1. 최상위 디렉터리 구조

본 제출 패키지(`말괄량이코물이_대구소상공인_AI_입지추천/`)는 단일 루트 디렉터리로 구성되어 있으며, 불필요한 임시 파일, 개발 캐시, 개인 식별 정보, 비공개 원천 데이터 없이 자립적으로 동작하도록 완전히 격리·패키징되었습니다.

```
말괄량이코물이_대구소상공인_AI_입지추천/
├── README.md                          # 서비스 개요, 주요 기능, 퀵스타트 종합 문서
├── README_JUDGE.md                    # 심사위원 5분 초고속 검증 가이드
├── requirements.txt                   # 프로덕션 실행 및 검증에 필요한 최소 필수 패키지
├── .env.example                       # 환경변수 예시 파일 (비밀키 및 토큰 미포함)
├── LICENSES.md                        # 코드, 패키지 및 공공데이터 라이선스 고지서
├── CHECKSUMS.sha256                   # 주요 파일 및 패키지 무결성 SHA-256 해시 목록
├── submission_manifest.json           # 공모전 공식 제출 메타데이터 및 환경 명세서
│
├── app/                               # 사용자 대시보드 웹 애플리케이션 계층
│   ├── app.py                         # Streamlit 메인 엔트리포인트 UI 스크립트
│   └── assets/                        # 대시보드 로고 및 배너 이미지 자산
│       ├── daegu_dashboard_hero.png   # 메인 히어로 배너 이미지
│       └── im_bank_logo.png           # iM뱅크 공모전 공식 로고
│
├── src/                               # 추천 알고리즘 및 피처 엔지니어링 코어 모듈
│   ├── features/                      # 지리 공간 및 교통 피처 생성 파이프라인
│   │   ├── __init__.py                # 모듈 패키징 초기화 파일
│   │   └── bus_features.py            # 시내버스 정류소-이용량 조인 및 동 단위 집계 모듈
│   └── recommendation/                # 입지 추천 알고리즘 및 XAI 설명 생성 모듈
│       ├── __init__.py                # 모듈 패키징 초기화 파일
│       ├── scoring.py                 # 초기 기준선(Baseline) 컴포넌트 점수 산출기
│       ├── improved.py                # 도시철도 역세권 가중 접근성 고도화 모듈
│       ├── transit_enhanced.py        # Candidate B(철도 70% + 버스 30%) 통합 모델
│       ├── feature_builder.py         # 150개 행정동 업종/타깃 피처 동적 결합기
│       ├── personalization.py         # 6대 가중치 프리셋 및 100% 정규화 엔진
│       ├── ranking.py                 # 1~150위 순위 정렬 및 동점자 방어 로직
│       ├── explain.py                 # 100% 수치 기반 설명 가능한 AI(XAI) 문장 생성기
│       └── sensitivity.py             # 가중치 민감도 및 순위 안정성 분석 모듈
│
├── data/                              # 프로덕션 서빙용 정제 데이터셋
│   ├── processed/                     # 전처리 완료된 Feature Mart 및 지오메트리
│   │   ├── feature_mart/              # 행정동 단위 상권/인구/점포 공간통계 피처마트
│   │   │   ├── commercial_feature_mart_dong.parquet
│   │   │   ├── commercial_feature_mart_dong.csv
│   │   │   ├── commercial_feature_mart_dong_category.parquet
│   │   │   ├── commercial_feature_mart_dong_category.csv
│   │   │   └── store_spatial_features.parquet
│   │   ├── geojson/                   # 150개 행정동 법정 경계 폴리곤
│   │   │   └── 대구_행정동_경계_20230701.geojson
│   │   ├── transit/                   # 대중교통 인프라 피처
│   │   │   ├── bus/                   # 시내버스 150개 동 피처 및 정류소 공간데이터
│   │   │   │   ├── daegu_bus_dong_features.parquet
│   │   │   │   ├── daegu_bus_dong_features.csv
│   │   │   │   └── daegu_bus_stops_processed.parquet
│   │   │   └── 대구도시철도_역별_위경도좌표.csv # 도시철도 94개 역 좌표
│   │   └── recommendation_scores.parquet # 사전 계산된 추천 점수 벤치마크
│   ├── raw/bus/                       # Phase 8 테스트 재현용 공공 버스 원천 데이터
│   │   ├── 대구광역시_시내버스 정류소 위치정보_20250903.csv
│   │   └── 대구광역시_시내버스  정류소별 월별 이용자수_20260731/
│   │       └── 시내버스 정류소별 월별 이용자수(2026-01~07).csv
│   └── README_DATA.md                 # 데이터 카탈로그 및 피처 정의서
│
├── reports/                           # 재현성 검증용 벤치마크 데이터
│   └── phase7_demo_results.json       # 6대 대표 데모 시나리오 일치성 검증 기준 JSON
│
├── scripts/                           # 실행 도구 및 Phase 6~15 자동화 테스트
│   ├── run_app.sh                     # macOS / Linux 원클릭 서비스 실행 셸 스크립트
│   ├── run_app.bat                    # Windows PowerShell 원클릭 실행 배치 파일
│   ├── run_phase6_tests.py            # Phase 6: 기본 추천 엔진/민감도 테스트 (10개)
│   ├── run_phase7_validation.py       # Phase 7: 도시철도 모델/데모 일치성 테스트 (12개)
│   ├── run_phase8_tests.py            # Phase 8: 버스 데이터 통합/커버리지 테스트 (10개)
│   ├── run_phase9_tests.py            # Phase 9: Candidate B 통합 무결성 테스트 (10개)
│   ├── run_phase10_tests.py           # Phase 10: UI Release Candidate QA 테스트 (10개)
│   ├── run_phase14c_tests.py          # Phase 14C: Baseline 모델 미진입 필터 방어 테스트 (6개)
│   ├── run_phase15_hardening_tests.py # Phase 15: 최종 하드닝 테스트 (12개)
│   ├── run_phase16_interactive_regression.py # Phase 16: 실제 UI 버그 회귀 테스트 (12개)
│   ├── run_phase17_python_compat_tests.py # Phase 17: Python 호환성/재현성 테스트 (7개)
│   ├── run_phase19_crosslayer_consistency.py # Phase 19: Cross-Layer 정합성 테스트 (14개)
│   ├── run_phase20_data_ui_integrity.py # Phase 20: 데이터·UI 정합성 테스트 (14개)
│   ├── run_phase21_final_defect_closure.py # Phase 21: 최종 결함 종결 테스트 (15개)
│   └── verify_phase16_browser.py      # Phase 16: Chromium 전체 UI 검증
│
├── docs/                              # 심사위원 검증 및 아키텍처 상세 문서
│   ├── PROJECT_STRUCTURE.md           # 상세 프로젝트 구조 안내 (본 파일)
│   ├── DATA_SOURCES.md                # 공공데이터 출처, 수집주기, 라이선스 명세
│   ├── MODEL_CARD.md                  # 다기준 추천 모델 사양서, 수식, 한계 명시
│   ├── REPRODUCIBILITY.md             # 환경 재현성, 결정론적 보장, 데모 기대값
│   └── TEST_REPORT.md                 # 132개 전체 회귀 테스트 상세 보고서
│
└── screenshots/                       # 고해상도(4K Retina) 서비스 실행 캡처 (A~D)
    ├── 01_main_recommendation.png     # [A] 메인 추천 결과 대시보드 및 Top 5 카드
    ├── 02_transit_map.png             # [B] Folium 인터랙티브 행정동 및 철도망 지도
    ├── 03_explainable_analysis.png    # [C] 100% 수치 기반 XAI 추천 사유 및 레이더 차트
    └── 04_model_comparison.png        # [D] 모델 비교 및 Spearman 상관계수 분석 화면
```

---

## 2. 경로 독립성 및 이식성 설계 (Portability Architecture)

1. **상대경로 동적 탐색 (`Path(__file__).resolve()`)**:
   - `app/app.py`, `src/features/bus_features.py`, 모든 테스트 스크립트(`scripts/run_phase*.py`)는 자체 파일 위치를 기준으로 프로젝트 루트 디렉터리를 동적으로 계산합니다.
   - 예시:
     ```python
     ROOT_DIR = Path(__file__).resolve().parent.parent
     DATA_DIR = ROOT_DIR / "data" / "processed"
     ```
   - 특정 운영체제나 개발 환경의 로컬 절대경로가 코드 내에 단 한 줄도 하드코딩되어 있지 않습니다.
2. **크로스 플랫폼 호환성**:
   - `pathlib.Path`를 전면 채택하여 슬래시(`/`)와 역슬래시(`\`)의 OS 간 차이를 자동으로 정규화합니다.
   - macOS(ARM/Intel), Linux(Ubuntu/Debian), Windows 10/11 전 환경에서 별도 코드 수정 없이 그대로 실행됩니다.
3. **오프라인 동작 완전 자립성**:
   - 실행에 필요한 모든 Feature Mart와 공간 경계 파일이 패키지 내부에 포함되어 있어 외부 인터넷 연결이 제한된 심사 환경에서도 로컬에서 100% 정상 작동합니다.

---

## 3. 계층별 상세 역할

### A. Presentation Layer (`app/`)
- **`app/app.py`**:
  - Streamlit 기반의 대화형 웹 인터페이스로, 사이드바를 통한 조건 설정, 실시간 입지 스코어링, Folium 인터랙티브 지도 렌더링, XAI 설명 카드 출력, 150개 동 CSV 다운로드 기능을 일체형으로 제공합니다.
  - 보안 강화: Folium 지도는 `get_root().render()` 방식을 채택하여 노트북 환경의 보안 경고 및 불필요한 스크립트 삽입을 원천 차단했습니다.

### B. Business & Algorithm Layer (`src/`)
- **`src/recommendation/feature_builder.py`**:
  - 예비 창업자가 선택한 업종(6대 대/중분류)과 타깃 연령층(10대~60대)에 따라 150개 행정동 피처마트에서 해당 데이터를 동적으로 슬라이싱하고 표준 피처 매트릭스를 조립합니다.
- **`src/recommendation/transit_enhanced.py`**:
  - Phase 8/9에서 도입된 **Candidate B 모델**의 핵심 엔진입니다. 도시철도 역세권 감쇄 점수(70%)와 버스 정류소 밀도 및 일평균 승하차량 점수(30%)를 백분위 랭크 기반으로 결합하여 150개 동의 통합 대중교통 접근성 지수를 산출합니다.
- **`src/recommendation/personalization.py`**:
  - 사용자가 슬라이더로 입력한 6대 컴포넌트 가중치를 합계 1.0(100%)으로 자동 정규화하며, 비정상 음수값이나 전 가중치 0 입력 시 기본 균형형 가중치로 안전하게 복원하는 방어 로직을 수행합니다.
- **`src/recommendation/explain.py`**:
  - 추천된 상위 5개 동에 대해 실제 지표값(예: 2030 인구 수, 정류소 수, 경쟁 점포 수)과 대구시 전체 대비 백분위 순위를 바인딩하여 거짓 정보가 없는 투명한 설명 텍스트를 생성합니다.

### C. Data Layer (`data/`)
- **`data/processed/feature_mart/`**:
  - 대구시 상가업소정보 11.8만 건과 주민등록인구 237만 명, 부설주차장 대장을 공간 결합(Spatial Join)하여 생성한 고효율 Parquet 포맷 피처마트입니다.
- **`data/processed/geojson/`**:
  - 2023년 7월 군위군 대구 편입 이후 기준의 150개 행정동 공식 법정 경계를 담고 있는 GeoJSON 데이터입니다.

### D. Quality Assurance Layer (`scripts/`)
- 기존 Phase 6~20 117개와 Phase 21 15개, 총 132개 회귀 테스트를 독립 스크립트로 재현할 수 있습니다.

---
**팀 말괄량이코물이 | 2026 AI Blockchain Challenge in Daegu**
