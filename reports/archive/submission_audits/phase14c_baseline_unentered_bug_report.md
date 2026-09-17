# Phase 14C: Baseline 모델 미진입 상권 필터 KeyError 결함 감사 및 조치 보고서

- **팀명**: 말괄량이코물이
- **공모전**: 2026 AI Blockchain Challenge in Daegu (소상공인·골목상권 디지털 금융)
- **과제명**: 대구 소상공인 AI 상권·창업 입지 추천 서비스
- **검증 일시**: 2026-09-09
- **최종 판정**: 🟢 BUG FIXED / NEW ZIP READY (무결성 100% 검증 완료)

---

## 1. 결함 보고 및 재현 결과

### 1.1 보고된 증상
- **환경**: Streamlit 좌측 사이드바 `⚙️ 모델 버전 및 대중교통 설정`
- **조작**:
  1. 모델 선택: `초기 기준선 모델 (도시철도 단순 거리)` (Phase 5 BASELINE)
  2. 필터 체크: `미진입 상권(0점포) 완전 제외` 체크박스 활성화
- **결과**: `KeyError: 'is_unentered'` 예외 발생으로 Streamlit 대시보드 강제 크래시 및 렌더링 중단.

### 1.2 원인 분석 (Root Cause)
1. **스코어링 함수 출력 스키마 불일치**:
   - `improved.py`의 `calculate_improved_scores()`와 `transit_enhanced.py`의 `calculate_enhanced_scores()`는 0점포 식별 컬럼(`is_unentered`)과 상권 구분 컬럼(`market_status`)을 기본 반환하도록 구현되어 있었습니다.
   - 반면, 초기 순수 기준선 모델인 `scoring.py`의 `calculate_component_scores()` + `compute_total_score()`는 기본 6대 컴포넌트 점수와 `cat_store_count`만을 반환하고 `is_unentered` 컬럼을 생성하지 않았습니다.
2. **UI 필터링 가드 부재**:
   - `app/app.py` 920행의 필터링 블록에서 `unentered_mask = active_ranked["is_unentered"].astype(bool)`로 직접 접근하면서, `is_unentered`가 결측된 Baseline 데이터프레임에서 `KeyError`가 발생하였습니다.

---

## 2. 최소 침습적 수정 (Semantic-Preserving Fix)

비즈니스 로직, 추천 점수 계산식, 가중치, 기존 52개 테스트에 영향을 주지 않도록 **Option A(방어적 안전 가드)와 Option B(스키마 통일성 보완)**를 동시 적용하였습니다.

### 2.1 적용 코드 (`app/app.py` lines 906-929)

```python
# 3. 활성 모델 선택
if model_mode == MODEL_MODE_BASELINE:
    raw_base_scored = compute_total_score(calculate_component_scores(feat_df.copy()), weights=norm_weights)
    active_ranked = rank_locations(raw_base_scored)
    # Option B: Baseline 출력 스키마 통일 (is_unentered 및 market_status 필드 보완)
    active_ranked["is_unentered"] = active_ranked["cat_store_count"].fillna(0).lt(1)
    active_ranked["market_status"] = np.where(
        ~active_ranked["is_unentered"],
        "기준선 분석 상권",
        "미진입 상권 (점포 0개)"
    )
elif model_mode == MODEL_MODE_SUBWAY_IMPROVED:
    active_ranked = base_ranked
else:  # Default: MODEL_MODE_INTEGRATED (Candidate B)
    active_ranked = cand_b_ranked

if filter_unentered_val:
    # Option A & B 통합 안전 가드: is_unentered 및 점포수 기준 완전 제외
    if "is_unentered" in active_ranked.columns:
        unentered_mask = active_ranked["is_unentered"].astype(bool)
    else:
        unentered_mask = active_ranked["cat_store_count"].fillna(0).lt(1)
    active_ranked = active_ranked[~unentered_mask].reset_index(drop=True)
    active_ranked["rank"] = range(1, len(active_ranked) + 1)
```

### 2.2 부가 효과
- `market_status` 컬럼이 Baseline 모드에서도 정상 공급되어, 하단 Tab 3의 비교 테이블(`active_ranked[["adm_cd2", "rank", ..., "market_status"]]`)에서 발생할 수 있었던 2차 잠재적 KeyError까지 원천 차단되었습니다.

---

## 3. 정량적 검증 및 점수 불변성 입증

### 3.1 숙박(Lodging) 업종 0점포 23개 행정동 제외 검증
대구광역시 150개 행정동 중 숙박 업종 등록 점포가 0개인 행정동은 정확히 23개입니다.

| 모델 모드 | 미진입 필터 OFF (150개 동) | 미진입 필터 ON (127개 동) | Top 1 행정동 | Top 1 점수 | 순위 연속성 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **기준선 (Baseline)** | 150개 전수 분석 | **127개 (23개 제외)** | 달서구 감삼동 | **77.00점** | [1..127] 완벽 |
| **도시철도 (Subway Improved)** | 150개 전수 분석 | **127개 (23개 제외)** | 달서구 감삼동 | **77.00점** | [1..127] 완벽 |
| **통합 (Candidate B)** | 150개 전수 분석 | **127개 (23개 제외)** | 달서구 감삼동 | **75.82점** | [1..127] 완벽 |

### 3.2 체크박스 해제 시 점수 100% 보존 검증 (Zero Regression)
- 체크박스가 비활성화된 기본 상태에서는 150개 동 전수가 유지되며, 기존 Phase 5/7 기준선 점수와 100% 동일함이 검증되었습니다.
  - 카페 + 2030 청년층: 1위 동구 신암4동 **77.93점** (오차 0.00)
  - 숙박 + 2030 청년층: 1위 달서구 감삼동 **77.00점** (오차 0.00)
  - 한식 + 전체 인구: 1위 달서구 진천동 **71.54점** (오차 0.00)

---

## 4. 신규 자동화 회귀 테스트 스위트 (`scripts/run_phase14c_tests.py`)

총 6개의 엄격한 단위 및 방어 검증 항목으로 구성된 신규 테스트 스위트를 작성하여 프로덕션 파이프라인에 통합하였습니다.

```
===========================================================================
PHASE 14C: Baseline 모델 미진입 상권 필터 KeyError 방어 및 회귀 검증 스위트
===========================================================================
[PASS] Test 1 (Test A): Baseline + exclude_unentered=False 150개 동 전수 분석 및 기준선 점수 100% 보존 검증 통과
[PASS] Test 2 (Test B): Baseline + exclude_unentered=True KeyError 0, 정확히 127개 동 필터링 및 1..127 순위 검증 통과
[PASS] Test 3 (Test C): Candidate B + exclude_unentered=True 127개 동 및 1위 감삼동(75.82점) 무결성 통과
[PASS] Test 4 (Test D): Subway Improved + exclude_unentered=True 127개 동 및 1위 감삼동(77.00점) 무결성 통과
[PASS] Test 5 (Test E): 3종 모델(Baseline/Improved/Candidate B) 출력 스키마 통일성 및 결측치 0 검증 통과
[PASS] Test 6 (Test F): app.py 방어 코드(Option A+B) 구문 검증 및 결측 컬럼 런타임 시뮬레이션 통과
===========================================================================
ALL 6 PHASE 14C AUTOMATED TESTS PASSED! (100%)
===========================================================================
```

### 전수 자동화 회귀 테스트 종합 현황 (58/58 PASS)
1. Phase 6 (추천 코어 & 민감도): 10/10 PASS
2. Phase 7 (도시철도 & 데모 일치성): 12/12 PASS
3. Phase 8 (시내버스 통합 & 커버리지): 10/10 PASS
4. Phase 9 (Candidate B 정식 통합): 10/10 PASS
5. Phase 10 (Streamlit UI 최종 QA): 10/10 PASS
6. **Phase 14C (미진입 상권 필터 방어)**: **6/6 PASS**
- **총합**: **58/58 PASS (통과율 100%)**

---

## 5. 실제 브라우저 Playwright E2E 검증

- **실행 포트**: 로컬 8508 포트
- **검증 절차**:
  1. 사이드바 `초기 기준선 모델 (도시철도 단순 거리)` 선택
  2. `미진입 상권(0점포) 완전 제외` 체크박스 클릭 (활성화)
  3. 창업 희망 업종 `숙박` 선택
- **결과**:
  - UI 예외 및 에러 다이얼로그 발생: **0건 (KeyError 완전 박멸)**
  - Top 1 카드: `대구광역시 달서구 감삼동` (77.0점) 정상 렌더링
  - 대화형 Folium 맵 및 하단 데이터프레임 정상 출력 확인

---

## 6. 제출 패키지 및 Clean Room 재검증

### 6.1 스테이징 동기화
- `submission/package/말괄량이코물이_대구소상공인_AI_입지추천/`에 수정된 `app/app.py` 및 신규 `scripts/run_phase14c_tests.py`를 복사.
- `submission_manifest.json`, `README.md`, `README_JUDGE.md`, `docs/TEST_REPORT.md`, `docs/PROJECT_STRUCTURE.md`, `docs/REPRODUCIBILITY.md` 6개 문서의 테스트 수치를 58개로 일괄 갱신.
- `CHECKSUMS.sha256` 53개 파일 전수 재계산 및 `shasum -c` 100% OK 검증.

### 6.2 신규 최종 ZIP 생성
- **생성 파일명**: `submission/말괄량이코물이_대구소상공인_AI_입지추천_제출코드_최종_v2.zip`
- **파일 크기**: **15.69 MB** (총 54개 파일, 단일 최상위 루트 디렉터리 구조)
- **기존 ZIP 보존**:
  - `submission/말괄량이코물이_대구소상공인_AI_입지추천_제출코드_최종.zip` (보존 완료)
  - `submission/말괄량이코물이_대구소상공인_AI_입지추천_제출코드.zip` (보존 완료)

### 6.3 독립 격리 환경(Clean Room) 검증
- **테스트 디렉터리**: `/tmp/clean_room_v2/`
- **검증 항목**:
  1. ZIP 무손실 압축 해제 확인: OK
  2. SHA-256 체크섬 53개 파일 전수 일치 확인: OK
  3. Phase 6~14C 전체 58개 테스트 연속 실행: **58/58 PASS (100%)**
  4. 헤드리스 Streamlit 서버 기동 및 바이트코드 컴파일: **정상 기동 (Traceback 0건)**

---

## 7. 최종 결론

`기존 기준선 모델`에서 `미진입 상권(0점포) 완전 제외` 활성화 시 발생하던 `KeyError: 'is_unentered'` 결함이 완벽히 해결되었으며, 전 모델에 걸친 스키마 통일성과 런타임 방어 코드가 구축되었습니다. 기존 모든 수치와 모델 결과의 불변성이 100% 입증되었으므로, **신규 ZIP 패키지(`..._제출코드_최종_v2.zip`)의 배포 및 제출을 공식 승인**합니다.
