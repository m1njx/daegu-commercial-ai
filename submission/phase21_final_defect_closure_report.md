# Phase 21 Final Defect Closure Report

## 1. Executive Verdict

🟢 **ALL KNOWN DEFECTS CLOSED / FINAL READY**

실측 및 코드 감사로 도출된 잔존 결함 11건과 감사 과정에서 추가 식별된 Phase 8 Spearman 순위 무관 1.0000 버그(총 12건)를 전수 종결(REPRODUCED → FIXED → TESTED → DOCUMENTED)했습니다. 모델 공식, 추천 가중치, Feature Mart 핵심 수치는 일체 변경하지 않았으며, 모든 수정은 132대 자동화 회귀 테스트(132/132 PASS, 100%), Playwright 브라우저 실조작 검증(6개 데모·3개 모델·Tab 2/3/5·CSV BOM 바이트), 독립 클린룸(/tmp/clean_room_phase21) 격리 검증을 전수 통과했습니다.

---

## 2. Issues Matrix (11 Issues + 1 Test Suite Fix)

| ID | Severity | Before | Root Cause | Fix | Runtime Verification | Status |
|---|---|---|---|---|---|:---:|
| **ISSUE-01** | Medium | `display_df.to_csv(index=False, encoding="utf-8-sig")` | `path_or_buf=None` 시 pandas가 `str`을 반환하여 BOM 바이트가 전달되지 않음 | `.to_csv(index=False).encode("utf-8-sig")` 바이트 인코딩 적용 | 헤더 첫 3바이트 `\xef\xbb\xbf` 확인 및 3개 모델 브라우저 다운로드 실측 완료 | 🟢 CLOSED |
| **ISSUE-02** | Medium | `requirements.txt`에 `streamlit>=1.33.0` 표기 | `st.dataframe(..., width="stretch")`는 Streamlit 1.49.0+ 필요 | `streamlit>=1.49.0`으로 최소 버전 계약 정합화 | 클린룸 환경에서 의존성 및 Streamlit 정상 기동 확인 | 🟢 CLOSED |
| **ISSUE-03** | Low | 미사용 함수 `render_sub_rank_card` 및 구 섹션 주석 존재 | Top 2~5 카드가 컴팩트 카드로 통합된 후 구 렌더러 방치 | `render_sub_rank_card` 및 stale 주석 완전 삭제 | AST 검증 및 런타임 렌더러 참조 무결성 확인 | 🟢 CLOSED |
| **ISSUE-04** | Medium | Demo 4 라벨에 `학원가 LQ 2.37` 오기 | 최신 데이터 갱신 후 범어1동 학원 LQ가 1.902로 변경되었으나 라벨 미반영 | `학원 특화도 LQ 1.90`으로 실제 데이터 일치 수정 | 실제 Feature Mart 행정동 특화도 1.902 계산 일치 확인 | 🟢 CLOSED |
| **ISSUE-05** | Medium | 문서에 Spearman 상관계수 범위 `0.9894 ~ 0.9943` 표기 | 과거 기본 가중치 기준 수치가 6개 공식 데모 프리셋 적용 범위와 혼용됨 | 6개 데모 프리셋 실측 범위 `0.9915 ~ 0.9969`로 문서 전수 동기화 | 6개 시나리오 런타임 계산 및 README/DOCS 전수 검증 | 🟢 CLOSED |
| **ISSUE-06** | Low | Spearman 델타 캡션에 `"0.985 이상 매우 안정적"` 고정 | rho 값이 0.985 미만으로 변동되어도 고정 안내 문구 노출 | `describe_rank_similarity(rho)` 3단계 동적 분기 함수 도입 | 0.99, 0.9757, 0.90 임계점별 안내 문구 동적 표출 확인 | 🟢 CLOSED |
| **ISSUE-07** | Medium | Tab 5 제목 및 다운로드 버튼에 `"150개 행정동"` 하드코딩 | 미진입 상권(0점포) 제외 시 127개로 축소되나 문구가 고정됨 | `result_count = len(active_ranked)` 동적 카운트 바인딩 | 체크박스 토글 시 127개로 동적 갱신 및 다운로드 라벨 일치 | 🟢 CLOSED |
| **ISSUE-08** | Low | 철도 및 버스 데이터 관측 기간 표현 모호 | 철도는 212일 일별 원천, 버스는 월별 집계를 212일로 나눈 일평균 | UI 및 문서에 관측 주기 및 집계 방식 명시적 구분 기술 | Tab 2 상세 분석 화면 문구 및 모델 카드 동기화 | 🟢 CLOSED |
| **ISSUE-09** | Medium | Demo 6 라벨에 `"감삼동 1위 / 0점포 왜곡 방어 실증"` 오기 | 감삼동은 실제 숙박 점포 6개 보유 지역으로 0점포 행정동이 아님 | `"감삼동 1위 / 미진입 상권 보정 비교"`로 명칭 정정 | 감삼동 `cat_store_count == 6` 실측 및 UI 라벨 확인 | 🟢 CLOSED |
| **ISSUE-10** | High | Baseline 0점포 행정동 설명에 `"동종 업종 시너지"` 허위 생성 가능 | `explain.py`에서 `industry_fit_score >= 65`만 검사하고 점포수 미검사 | `cat_store_count > 0` 가드 조건문 추가 | 0점포 가상 행정동 입력 시 시너지 문구 억제 확인 | 🟢 CLOSED |
| **ISSUE-11** | Medium | 버스 원천 파일 탐색 시 중복 파일 존재 시 비결정론적 선택 | `find_bus_raw_files`가 다중 매칭 시 명시적 오류 없이 임의 선택 | 후보가 2개 이상일 경우 명시적 `RuntimeError` 발생 | 임시 폴더 다중 후보 주입 테스트로 즉시 예외 포착 검증 | 🟢 CLOSED |
| **ISSUE-12** | High | Phase 8 Test 8에서 Spearman rho가 항상 1.0000 출력 | `b_rank["rank"]`와 `e_rank["rank"]`를 `adm_cd2` 조인 없이 단순 비교 | `b_rank.merge(e_rank, on="adm_cd2")`로 행정동 기준 정렬 후 계산 | 기본 가중치 최저 rho 0.9894, 공식 데모 0.9915~0.9969 실측 확인 | 🟢 CLOSED |

---

## 3. CSV BOM (ISSUE-01)

- **수정 파일**: `app/app.py`
- **변경 사항**:
  ```python
  csv_bytes = display_df.to_csv(index=False).encode("utf-8-sig")
  st.download_button(..., data=csv_bytes, mime="text/csv")
  ```
- **검증 결과**:
  - 생성된 페이로드 바이너리의 첫 3바이트가 `\xef\xbb\xbf` (UTF-8-SIG BOM)임을 검증 통과.
  - Playwright 브라우저 자동화를 통해 3대 모델(통합 대중교통, 도시철도 중심, 초기 기준선)의 CSV 다운로드를 직접 수행하고 한글 컬럼명 깨짐 없음을 확인.

---

## 4. Streamlit Version Contract (ISSUE-02)

- **수정 파일**: `requirements.txt`
- **변경 사항**: `streamlit>=1.33.0` → `streamlit>=1.49.0`
- **검증 결과**:
  - `app/app.py` 전역에서 사용되는 `st.dataframe(..., width="stretch")` 구문은 Streamlit 1.49.0 미만 버전에서 호환되지 않음.
  - 최소 버전 요구사항을 명시하여 클린룸 및 신규 환경 설치 시 런타임 호환성 에러를 원천 차단.

---

## 5. Dead Code Removal (ISSUE-03)

- **수정 파일**: `app/app.py`
- **변경 사항**:
  - 호출되지 않는 레거시 함수 `render_sub_rank_card` 완전 삭제.
  - 불일치하는 주석 `SECTION 3: 🥈 2위 ~ 5위 카드 표시` 정리.
- **검증 결과**:
  - Python AST 분석을 통해 해당 심볼이 파일 내에 잔존하지 않음을 확인.
  - Top 5 표시는 컴팩트 카드(`render_compact_rank_card`)로 일관되게 렌더링됨을 검증.

---

## 6. Demo 4 Location Quotient Label (ISSUE-04)

- **수정 파일**: `app/app.py`
- **변경 사항**: `"학원가 LQ 2.37"` → `"학원 특화도 LQ 1.90"`
- **검증 결과**:
  - 범어1동 학원 업종의 실제 Feature Mart LQ는 1.902로 계산됨.
  - UI 데모 선택 셀렉트박스와 설명 텍스트가 실제 피처 수치와 100% 일치.

---

## 7. Spearman Correlation Range (ISSUE-05)

- **수정 파일**: `README.md`, `README_JUDGE.md`, `docs/MODEL_CARD.md`, `docs/REPRODUCIBILITY.md`
- **실측 수치**:
  - 기본 균형형 가중치 기준 6개 업종/타깃: `0.9894 ~ 0.9943` (최저 한식 0.9894, 최고 학원 0.9943)
  - 6개 공식 데모 시나리오(각각의 최적 프리셋 적용 시):
    - 카페 + 2030 (기본 균형형): **0.9940**
    - 한식 + 전체 (배후 수요 집중형): **0.9924**
    - 미용실 + 2030 (기본 균형형): **0.9937**
    - 학원 + 10대 (타깃 고객 집중형): **0.9969**
    - 종합소매 + 전체 (기본 균형형): **0.9915**
    - 숙박 + 2030 (기본 균형형): **0.9940**
    - **공식 데모 범위**: `0.9915 ~ 0.9969`
- **검증 결과**: 모든 심사위원 안내 문서 및 모델 카드에서 과거 수치를 `0.9915 ~ 0.9969`로 완벽히 일치화.

---

## 8. Dynamic Spearman Metric Caption (ISSUE-06)

- **수정 파일**: `app/app.py`
- **변경 사항**:
  ```python
  def describe_rank_similarity(rho_val: float) -> str:
      if rho_val >= 0.985:
          return "높은 순위 유사도"
      elif rho_val >= 0.950:
          return "일부 순위 변화 (중간 수준 유사도)"
      else:
          return "순위 변화 확인 필요"
  ```
- **검증 결과**:
  - 임의 가중치 변경으로 rho가 하락할 때도 정직하고 객관적인 안내 문구가 출력됨을 확인. 과도한 단정적 주장("매우 안정적") 배제 완료.

---

## 9. Dynamic Dong Count (ISSUE-07)

- **수정 파일**: `app/app.py`
- **변경 사항**: 고정 문자열 `"150개"` 대신 `result_count = len(active_ranked)`를 바인딩하여 필터링 상태에 따라 동적으로 라벨링.
- **검증 결과**: 숙박 업종에서 "미진입 상권(0점포) 완전 제외" 활성화 시 헤더 및 다운로드 버튼이 `"127개"`로 즉시 갱신됨을 Playwright로 실측 확인.

---

## 10. Transit Period Wording (ISSUE-08)

- **수정 파일**: `app/app.py`, `docs/MODEL_CARD.md`
- **변경 사항**:
  - 도시철도: "2026년 1~7월 일별 관측(212일)"
  - 시내버스: "같은 기간의 월별 집계를 212일로 나눈 일평균"
- **검증 결과**: 데이터 소스 간 집계 단위의 차이를 심사위원이 오해하지 않도록 정확하고 투명하게 명시 완료.

---

## 11. Demo 6 Zero-Store Label Correction (ISSUE-09)

- **수정 파일**: `app/app.py`
- **변경 사항**: `"감삼동 1위 / 0점포 왜곡 방어 실증"` → `"감삼동 1위 / 미진입 상권 보정 비교"`
- **검증 결과**: 감삼동은 실제 숙박 업소 6개 보유 지역(`cat_store_count == 6`)이며, 감삼동 자체를 0점포 상권으로 오인하게 만드는 라벨 결함 종결.

---

## 12. Baseline Explanation Zero-Store Guard (ISSUE-10)

- **수정 파일**: `src/recommendation/explain.py`
- **변경 사항**:
  ```python
  if row.get("industry_fit_score", 0) >= 65 and row.get("cat_store_count", 0) > 0:
      # 동종 업종 시너지 강점 출력
  ```
- **검증 결과**: 점포 수가 0인 행정동에 대해 "동종 업종 시너지"라는 모순된 설명이 생성되지 않도록 가드 완료.

---

## 13. Bus Raw File Discovery Robustness (ISSUE-11)

- **수정 파일**: `src/features/bus_features.py`
- **변경 사항**: 다중 후보 파일 발견 시 조용히 첫 번째 파일을 선택하지 않고 `RuntimeError(f"버스 ... CSV 후보가 여러 개입니다: {candidates}")`를 발생시켜 비결정론적 데이터 오염 방지.
- **검증 결과**: Phase 21 자동화 테스트 스위트 11번에서 임시 디렉토리 다중 주입 검증 통과.

---

## 14. Phase 20 Bus Data Integrity Preservation

Phase 20에서 확립된 원거리 동명이인 정류소 군집화 및 총량 보존 법칙이 100% 보존됨을 재확인했습니다:
- **원천 매칭 총량 보존**: 매칭 승하차 159,974,409건 / 212일 = 754,596.2688679246명/일
- **정류소 표지판 합계**: 754,596.2688679246명/일 (오차 0.0)
- **150개 행정동 피처 합계**: 754,596.2688679246명/일 (오차 0.0)
- **동명이인 분리**: 달산1리(4개 군집), 달산2리(4개 군집), 수서2리(3개 군집) 공간 분리 유지.

---

## 15. Documentation Synchronization

아래 주요 문서 및 산출물 간 수치·라벨·팀명 완전 동기화:
1. `README.md`
2. `README_JUDGE.md`
3. `docs/MODEL_CARD.md`
4. `docs/REPRODUCIBILITY.md`
5. `docs/TEST_REPORT.md`
6. `docs/DATA_SOURCES.md`
7. `submission_manifest.json`
8. `submission/documents/제안 요약서.pdf` (Phase 21 검증 수치 132/132 및 0.9915~0.9969 동기화 완료)

---

## 16. Playwright Browser Acceptance

실제 Chromium 헤드리스 브라우저 조작 검증 결과:
- **6개 대표 데모 1위 및 점수**:
  - Demo 1 (카페+2030): 신암4동 (77.75) — PASS
  - Demo 2 (한식+전체): 상인1동 (77.47) — PASS
  - Demo 3 (미용실+2030): 칠성동 (75.45) — PASS
  - Demo 4 (학원+10대): 범어1동 (84.47, LQ 1.90) — PASS
  - Demo 5 (소매+전체): 상인1동 (72.22) — PASS
  - Demo 6 (숙박+2030): 감삼동 (75.82, 0점포 보정 비교) — PASS
- **Tab 2 (상세 분석)**: 150개 행정동 셀렉트박스 및 Folium 지도 렌더링 PASS
- **Tab 3 (모델 비교)**: 통합 대중교통 vs 도시철도 중심 모델 실시간 비교 및 동적 캡션 PASS
- **Tab 5 (데이터/분석)**: 필터링 조건 동적 행정동 수 카운트 및 3대 모델 UTF-8-SIG CSV 다운로드 PASS
- **브라우저 에러**: 콘솔 에러 0건, 페이지 에러 0건, 금지어 표출 0건.

---

## 17. Explanation Grounding Verification

- **검증 대상**: 6개 공식 데모의 Top 5 추천 행정동에 대한 설명 파티클 총 90개.
- **수치 불일치 (Mismatch)**: 0건 (90/90 완전 일치)
- **환각 (Hallucination)**: 0건
- **금지어 배제**: "비중가", "인원가", "여건가", "미크로", "2026 iM뱅크 데이터톤", "상권ON" 0건.

---

## 18. Existing Tests Execution (Phase 6 ~ 20)

| 스위트명 | 파일 경로 | 테스트 수 | 통과 수 | 통과율 |
|---|---|---:|---:|:---:|
| Phase 6: 기본 추천 엔진 및 민감도 | `scripts/run_phase6_tests.py` | 10 | 10 | 100% |
| Phase 7: 도시철도 모델 및 데모 일치성 | `scripts/run_phase7_validation.py` | 12 | 12 | 100% |
| Phase 8: 버스 데이터 통합 및 순위 안정성 | `scripts/run_phase8_tests.py` | 10 | 10 | 100% |
| Phase 9: Candidate B 정식 서비스 통합 | `scripts/run_phase9_tests.py` | 10 | 10 | 100% |
| Phase 10: Streamlit UI QA | `scripts/run_phase10_tests.py` | 10 | 10 | 100% |
| Phase 14C: Baseline 0점포 필터 방어 | `scripts/run_phase14c_tests.py` | 6 | 6 | 100% |
| Phase 15: Runtime/Schema/Claim 하드닝 | `scripts/run_phase15_hardening_tests.py` | 12 | 12 | 100% |
| Phase 16: 인터랙티브 회귀 및 설명 검증 | `scripts/run_phase16_interactive_regression.py` | 12 | 12 | 100% |
| Phase 17: Python 문법 호환성 | `scripts/run_phase17_python_compat_tests.py` | 7 | 7 | 100% |
| Phase 19: Cross-Layer 일관성 | `scripts/run_phase19_crosslayer_consistency.py` | 14 | 14 | 100% |
| Phase 20: 데이터·UI·제안서 정합성 | `scripts/run_phase20_data_ui_integrity.py` | 14 | 14 | 100% |
| **기존 회귀 소계** | | **117** | **117** | **100%** |

---

## 19. Phase 21 Dedicated Tests Execution

- **테스트 스위트**: `scripts/run_phase21_final_defect_closure.py`
- **테스트 항목 (15개)**:
  1. CSV 다운로드 UTF-8-SIG BOM 바이트 검증 — PASS
  2. Streamlit >= 1.49.0 요구사항 검증 — PASS
  3. `render_sub_rank_card` 데드코드 및 섹션 헤딩 삭제 검증 — PASS
  4. Demo 4 범어1동 학원 LQ 1.90 실측 일치 검증 — PASS
  5. 6개 공식 데모 Spearman rho 실측 범위 (0.9915~0.9969) 및 문서 동기화 검증 — PASS
  6. `describe_rank_similarity` 동적 캡션 3단계 분기 검증 — PASS
  7. Tab 5 동적 행정동 개수 및 다운로드 라벨 검증 — PASS
  8. 철도 212일 일별 vs 버스 212일 일평균 기간 표현 검증 — PASS
  9. Demo 6 감삼동 실제 점포수(6개) 및 라벨 수정 검증 — PASS
  10. Baseline 0점포 설명 생성 시 시너지 문구 차단 검증 — PASS
  11. 버스 원천 탐색 시 다중 후보 예외 발생 검증 — PASS
  12. Phase 20 정류소 공간 군집 및 승하차 총량 보존 검증 — PASS
  13. 심사 문서 내 구 결함 리터럴 배제 검증 — PASS
  14. 6개 공식 데모 1위 지역명 및 주요 팩트 일치 검증 — PASS
  15. Manifest 132개 테스트 회귀 일치성 검증 — PASS
- **결과**: **15 / 15 PASS (100%)**

---

## 20. Total Tests Summary

- **전체 자동 회귀 테스트 합계**: **132 / 132 PASS (100.0%)**
- **실패(Failed)**: 0건
- **스킵(Skipped)**: 0건

---

## 21. Clean Room Verification

`/tmp/clean_room_phase21/`에 최종 제출 ZIP을 독립 해제하여 검증을 완수했습니다:
- **Checksum 검증**: `CHECKSUMS.sha256`에 등록된 87개 파일 전수 `OK` 확인.
- **Python 바이트코드 컴파일**: `python3 -m compileall app src scripts` 43개 파일 전수 오류 0건 컴파일.
- **전체 132대 테스트 실행**: 클린룸 내부에서 12대 스위트 전수 실행 결과 132/132 PASS (100%).
- **독립 Streamlit 기동**: 포트 8503으로 클린룸 Streamlit 서버 독립 기동 및 헬스체크(200 OK) 확인.
- **클린룸 브라우저 실조작**: Playwright를 이용해 포트 8503 대상 6개 데모, 3대 모델, Tab 2/3/5, UTF-8-SIG CSV 다운로드 실측 전수 통과.
- **원본 경로 참조 배제**: 클린룸 코드 및 문서 내 개발자 로컬 경로(`kangminje04`, `Daegu_data`) 잔존 0건 확인.

---

## 22. Security and Hygiene Audit

- **Secret / API Key**: 0건 (원천 수집 스크립트용 `.env.example` 플레이스홀더 외 실키 없음)
- **개인정보 (PII)**: 0건
- **비공개 제한 데이터**: 0건
- **`.env` 실파일**: 0건
- **`.git` / `.venv` 디렉토리**: 0건
- **캐시 및 임시 파일**: `__pycache__` 0건, `*.pyc` 0건, `.DS_Store` 0건
- **HWPX 바이너리 패키징**: 0건
- **패키지 내 구버전 ZIP**: 0건
- **개인 로컬 절대경로**: 0건

---

## 23. Final ZIP Package

- **파일명**: `말괄량이코물이_대구소상공인_AI_입지추천_제출코드_FINAL_CLOSED.zip`
- **저장 위치**: `submission/말괄량이코물이_대구소상공인_AI_입지추천_제출코드_FINAL_CLOSED.zip`
- **파일 크기**: 39,237,907 Bytes (약 37.4 MB)
- **SHA-256 Checksum**:
  `26999633273661a21a6a08cf74e002effaa0b2d4eda333c89507d15db02fa663`

---

## 24. Remaining Issues

`Known reproducible issue: 0`

---

## 25. Final Verdict

🟢 **ALL KNOWN DEFECTS CLOSED / FINAL READY**

제27번 최종 수락 기준(11개 결함 + 1개 테스트 결함 수정, 전용 회귀 테스트, CSV BOM 실바이트, 최소 버전 계약, Demo 4 LQ 실측, 6개 데모 Spearman 실측 범위 일치, 동적 캡션, 동적 행정동 수, 교통 관측 기간 명시, Demo 6 점포수 오기 제거, Baseline 0점포 가드, 버스 원천 결정론적 탐색, Phase 20 총량 보존, 브라우저 실조작, 90개 설명 접지, 132/132 회귀 테스트, 클린룸 독립 검증, 보안/위생 전수 감사, 핵심 공식 불변)을 완벽하게 100% 충족하여 본 최종 제출 패키지를 🟢 FINAL READY로 판정합니다.
