# Judge Quick Verification Guide

**팀명**: 말괄량이코물이  
**프로젝트**: 대구 소상공인 AI 상권·창업 입지 추천 서비스  
**공모전**: 2026 AI Blockchain Challenge in Daegu (소상공인·골목상권 디지털 금융)  

본 문서는 심사위원께서 **5~10분 이내**에 프로젝트의 설치, 실행, 핵심 알고리즘, 추천 사유 설명성(XAI), 모델 비교, 자동화 테스트 무결성을 신속하게 검증하실 수 있도록 구성된 초고속 평가 가이드입니다.

---

## STEP 1: 환경 구성 (약 1분)

프로젝트 루트 디렉터리(`말괄량이코물이_대구소상공인_AI_입지추천/`)에서 다음 명령을 실행합니다.

검증된 Python 버전은 **3.10.21, 3.11.15, 3.14.5**입니다.

```bash
# 가상환경 생성 및 활성화 (macOS / Linux)
python3 -m venv .venv
source .venv/bin/activate

# 의존성 패키지 설치
pip install --upgrade pip
pip install -r requirements.txt
```

> **Windows 사용자**: `py -m venv .venv` 및 `.\venv\Scripts\Activate.ps1` 실행 후 동일하게 `pip install -r requirements.txt`를 실행합니다.

---

## STEP 2: Streamlit 대시보드 실행 (약 30초)

```bash
streamlit run app/app.py
```
- 터미널에 로컬 URL(`http://localhost:8501`)이 표시되며 브라우저가 자동 실행됩니다.
- 초기 로딩 시 대구 전역 150개 행정동, 11.8만 점포, 94개 철도역, 3,981개 버스 정류소 데이터를 메모리에 캐싱(약 1~2초 소요)합니다.

---

## STEP 3: 대표 추천 시나리오 1 확인 (기본 균형형)

가장 대표적인 창업 업종인 **카페**와 2030 청년 주민등록인구 타깃의 추천 결과를 확인합니다.

1. **좌측 사이드바 설정**:
   - **창업 희망 업종**: `카페` (기본값)
   - **주요 타깃 고객층**: `2030 청년 소비층 (20~39세)` (기본값)
   - **추천 모델 선택**: `통합 대중교통 모델 (권장 / 도시철도 70% + 시내버스 30%)` (기본값)
   - **가중치 프리셋**: `기본 균형형` (기본값)
2. **검증 포인트**:
   - **Top 1 추천지**: **대구광역시 동구 신암4동**
   - **종합 점수**: **약 77.75점**
   - **상권 특성**: KTX 동대구역 및 복합환승센터, 도시철도 1호선, 대규모 시내버스 결절점이 집중되어 배후수요와 대중교통 접근성이 모두 최상위권(100점 만점 기준 80점 이상)을 기록함을 확인하실 수 있습니다.

---

## STEP 4: 설명가능성(XAI) 및 타깃 집중 시나리오 2 확인

사설 학원 업종과 10대 이하(0~19세) 타깃 인구 집중 상권을 검증합니다.

1. **좌측 사이드바 설정 변경**:
   - **창업 희망 업종**: `학원`
   - **주요 타깃 고객층**: `10대 이하 (0~19세)`
   - **가중치 프리셋**: `타깃 고객 집중형 (트렌디/특화 소비)` 선택
2. **검증 포인트**:
   - **Top 1 추천지**: **대구광역시 수성구 범어1동**
   - **종합 점수**: **약 84.47점**
   - **사유 설명 확인**: 중앙 탭 **"📊 추천 1~5위 상세 분석 및 설명"**에서 범어1동 카드를 확인합니다.
     - 10대 학령인구 밀집도와 학원 업종 집중도가 수치 및 시내 백분위(상위 1%)로 투명하게 인용되는지 확인합니다.
     - 주관적 미사여구나 거짓 수치(Hallucination) 없이 100% Data-Grounded된 설명문이 생성됨을 확인하실 수 있습니다.

---

## STEP 5: 모델 간 정량 비교 및 비역세권 평가 개선 확인

본 프로젝트의 핵심 공학적 기여인 **도시철도-시내버스 통합 효과(Candidate B)**를 검증합니다.

1. **상단 탭 이동**:
   - 세 번째 탭인 **"⚖️ 도시철도 중심 개선 모델 vs 통합 대중교통 모델"** 클릭
2. **검증 포인트**:
   - **전체 순위 안정성**: 대구 전역 150개 행정동 대상 Spearman Rank Correlation이 $\\rho \\approx 0.9894 \\sim 0.9943$ 수준의 높은 순위 일관성을 유지함을 확인합니다.
   - **비역세권 접근성 지표 변화**: 도시철도역이 없는 91개 행정동에서 버스 지표를 포함할 때의 평균 접근성 점수 변화를 현재 조건에서 동적으로 확인합니다.

---

## STEP 6: 103개 자동화 회귀 테스트 검증

새 터미널 창을 열고, 프로젝트에 탑재된 10개 Phase 자동화 테스트 스위트를 실행하여 결측치, 이상치, 가중치 정규화, 회귀 일치성, 미진입 필터 및 Cross-Layer 정합성을 검증합니다.

```bash
# 기존 Phase 6~17 89개 + Phase 19 14개 = 총 103개
python scripts/run_phase6_tests.py
python scripts/run_phase7_validation.py
python scripts/run_phase8_tests.py
python scripts/run_phase9_tests.py
python scripts/run_phase10_tests.py
python scripts/run_phase14c_tests.py
python scripts/run_phase15_hardening_tests.py
python scripts/run_phase16_interactive_regression.py
python scripts/run_phase17_python_compat_tests.py
python scripts/run_phase19_crosslayer_consistency.py
```

### 기대 결과:
```
PHASE 6: ALL 10 TESTS PASSED (100%)
PHASE 7: ALL 12 TESTS PASSED (100%)
PHASE 8: ALL 10 TESTS PASSED (100%)
PHASE 9: ALL 10 TESTS PASSED (100%)
PHASE 10: ALL 10 TESTS PASSED (100%)
PHASE 14C: ALL 6 TESTS PASSED (100%)
PHASE 15: 12/12 PASS
PHASE 16: 12/12 PASS
PHASE 17: 7/7 PASS
PHASE 19: 14/14 PASS
==================================================
전체 103/103 테스트 통과
```

---

## 심사위원 질의 대응 요약

- **Q. 추천 점수가 매출을 의미하나요?**  
  **A.** 아닙니다. 본 모델은 다기준 의사결정(MCDM) 기법을 적용한 행정동 단위의 **상대적 입지 적합도 비교 점수(0~100점)**이며, 매출액이나 창업 성공률을 직접 추정하지 않습니다 ([docs/MODEL_CARD.md](docs/MODEL_CARD.md) 명시).
- **Q. 금융 및 정책자금 연동은 어떻게 되어 있나요?**  
  **A.** 본 제출 프로토타입은 1단계 공공데이터 기반 입지 추천 엔진을 온전하게 구현한 결과물이며, iM뱅크 Open API 및 정책자금 연동은 향후 본선 및 사업화 단계에서 구현할 **확장 로드맵**으로 명확히 구분되어 있습니다.
- **Q. 버스 데이터 결손 지역은 없나요?**  
  **A.** 대구 전역 3,981개 정류소 매핑 결과, 150개 전 행정동에 버스 정류소가 100% 정상 연결되어 결손이나 임의 Fallback(대치) 없이 완전하게 산출됩니다.

---
**팀 말괄량이코물이 드림**
