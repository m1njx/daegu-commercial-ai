# 환경 및 결과 재현성 가이드 (Reproducibility Guide)

**팀명**: 말괄량이코물이  
**프로젝트**: 대구 소상공인 AI 상권·창업 입지 추천 서비스  
**공모전**: 2026 AI Blockchain Challenge in Daegu  

본 문서는 심사위원이 제출 코드를 독립 환경에서 설치·실행하고, 본 패키지의 결정론적 추천 결과와 테스트 스위트를 재현하기 위한 기술 검증 가이드입니다.

---

## 1. 검증된 실행 환경 (Tested Environments)

- **실제 검증 운영체제**: macOS (Apple Silicon)
- **기타 운영체제**: Linux/Windows용 실행 명령과 상대경로 사용을 정적으로 점검했으며, 이번 감사 호스트에서는 직접 실행하지 않았습니다.
- **파이썬 버전 (Python)**:
  - 전체 테스트 및 Streamlit 실행 검증: Python 3.10.21, Python 3.11.15, Python 3.14.5
  - Python 3.10.21은 `FINAL_COMPAT.zip` Clean Room에서 신규 venv·requirements 설치·89/89 테스트·브라우저 smoke까지 독립 검증했으며, Phase 19 변경 후 전체 103개 회귀를 재검증
  - Python 3.12/3.13: 감사 호스트에 인터프리터가 없어 `NOT TESTED`
- **핵심 라이브러리 버전**:
  - `pandas>=2.0.0`
  - `numpy>=1.24.0`
  - `scipy>=1.10.0`
  - `geopandas>=1.0.0`
  - `shapely>=2.0.0`
  - `streamlit>=1.33.0`
  - `folium>=0.15.0`
  - `pyarrow>=15.0.0`

---

## 2. 100% 결정론적(Deterministic) 보장

본 추천 엔진은 확률적 난수 생성기(`random`, `numpy.random`), 비결정론적 딥러닝 가중치 초기화, 또는 외부 실시간 API 호출을 일절 포함하지 않습니다.

1. **난수 시드 무관 (Zero Seed Dependency)**:
   - 모든 순위와 점수는 정적 공공데이터와 수학적 선형 결합 수식에 의해 결정되므로, `seed` 설정 여부와 관계없이 언제나 100% 동일한 결과를 출력합니다.
2. **동점자 방어 결정론적 정렬 (Deterministic Tie-Breaking)**:
   - `ranking.py`는 실제 구현 순서인 `[total_score, demand_score, target_fit_score, pop_total]`을 모두 내림차순으로 정렬합니다. 현재 제출 데이터에서는 이 정렬키 조합이 행별로 고유하여 동일 입력의 순위가 결정론적으로 재현됩니다.

---

## 3. 대표 데모 시나리오별 기대 수치 (Exact Expected Outputs)

심사위원께서 Streamlit 대시보드 및 터미널에서 즉시 확인 가능한 3대 대표 시나리오의 재현 기준값입니다.

### 시나리오 1: 카페 창업 (2030 청년층 타깃 / 기본 균형형)
- **입력**: 업종 `카페`, 연령 `2030 청년 소비층`, 프리셋 `기본 균형형`, 모델 `통합 대중교통 모델`
- **Top 1 행정동**: **대구광역시 동구 신암4동**
- **기대 점수**: **77.75점**
- **특징**: 동대구역 복합환승센터 및 도시철도·시내버스 집결 효과로 대중교통 및 배후수요 동시 1위.

### 시나리오 2: 학원 창업 (10대 이하 타깃 / 타깃고객 집중형)
- **입력**: 업종 `학원`, 연령 `10대 이하 (0~19세)`, 프리셋 `타깃 고객 집중형 (트렌디/특화 소비)`, 모델 `통합 대중교통 모델`
- **Top 1 행정동**: **대구광역시 수성구 범어1동**
- **기대 점수**: **84.47점**
- **특징**: 대구 대표 명문 학군으로 10대 학령인구 및 사설 학원 밀집도가 대구시 최상위권 기록.

### 시나리오 3: 한식 음식점 창업 (전체 인구 / 모델 정량 비교)
- **입력**: 업종 `한식`, 연령 `전체`, 모델 비교 탭 이동
- **Spearman 순위 상관계수**: **약 0.9894 ~ 0.9943**
- **특징**: 도시철도 중심 개선 모델 대비 높은 순위 일관성을 유지하면서 비역세권 91개 동의 접근성 지표가 평균 $+3.81$점 변화함.

---

## 4. 103개 전체 회귀 테스트 재현 명령

제출 패키지에서 기존 Phase 6~17 89개와 Phase 19 Cross-Layer 정합성 14개를 순차 실행합니다.
아래 스위트의 기대 합계는 **103/103 PASS**입니다.

```bash
python scripts/run_phase6_tests.py       # 기대: ALL 10 TESTS PASSED (100%)
python scripts/run_phase7_validation.py  # 기대: ALL 12 TESTS PASSED (100%)
python scripts/run_phase8_tests.py       # 기대: ALL 10 TESTS PASSED (100%)
python scripts/run_phase9_tests.py       # 기대: ALL 10 TESTS PASSED (100%)
python scripts/run_phase10_tests.py      # 기대: ALL 10 TESTS PASSED (100%)
python scripts/run_phase14c_tests.py     # 기대: ALL 6 TESTS PASSED (100%)
python scripts/run_phase15_hardening_tests.py # 기대: PHASE 15: 12/12 PASS
python scripts/run_phase16_interactive_regression.py # 기대: PHASE 16: 12/12 PASS
python scripts/run_phase17_python_compat_tests.py # 기대: PHASE 17: 7/7 PASS
python scripts/run_phase19_crosslayer_consistency.py # 기대: PHASE 19: 14/14 PASS
```

총 소요 시간: 약 3~5초 이내에 전 스위트가 완료됩니다.

---
**팀 말괄량이코물이 | 2026 AI Blockchain Challenge in Daegu**
