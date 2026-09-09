# Phase 15 Final Submission Hardening Audit

## 1. Executive Summary

세 모델의 Runtime, Claim, Branch, Schema, UI를 재감사했다. 최신 코드에서 알려진 Baseline `is_unentered` crash는 이미 수정된 상태였으며 실제 UI에서 재현되지 않았다. Baseline 설명과 사용자 프리셋 및 제출 문서에 남은 승하차 데이터의 `유동인구` 오표현, 모델 비교 탭의 branch 명칭 불일치와 과도한 효과 표현을 최소 수정했다. 모델 공식, 가중치, Feature Mart 및 순위 공식은 변경하지 않았다.

## 2. Scope

`app/app.py`, `src/recommendation/` 전체, `src/features/`, Phase 6~10/14C 테스트, 제출 패키지 문서, CSV·지도·세션 상태·캐시·보안·Clean Room을 검사했다. Raw/Processed/Feature Mart 값과 모델 수식은 동결했다.

## 3. Model Branch Matrix

| 항목 | Integrated | Improved | Baseline |
|---|---|---|---|
| Scoring | `calculate_enhanced_scores(candidate_b)` | `calculate_enhanced_scores(baseline, is_improved=True)` | `calculate_component_scores` + `compute_total_score` |
| Feature preparation | `build_dong_industry_features` + bus columns | 동일 | 동일 |
| Explanation | `generate_enhanced_explanation` | `generate_improved_explanation` | `generate_explanation` |
| Ranking | `rank_locations` | `rank_locations` | `rank_locations` |
| Filter | `is_unentered` | `is_unentered` | 앱에서 `cat_store_count < 1`로 생성한 `is_unentered` |
| CSV / Map / Detail | `active_ranked` | `active_ranked` | `active_ranked` |

## 4. Issues Found

| ID | Severity | Branch | File | Root Cause | Impact | Status |
|---|---|---|---|---|---|---|
| BUG-001 | P0 | Baseline | `app/app.py` | 과거 결과 schema에 `is_unentered` 누락 | 필터 ON crash | 기존 수정 확인, 회귀 고정 |
| CLAIM-001 | P1 | Baseline | `src/recommendation/explain.py:48` | 승하차를 유동인구로 명명 | 통신 데이터 오인 | FIXED |
| CLAIM-002 | P1 | All/UI | `personalization.py` | 프리셋명에 유동인구 사용 | 데이터 의미 오인 | FIXED |
| CLAIM-003 | P1 | Docs | README_JUDGE, MODEL_CARD | 같은 용어가 문서에 잔존 | 심사 오인 | FIXED |
| CLAIM-004 | P2 | Compare | `app/app.py` | Improved 결과를 Baseline으로 표시 | 비교 대상 오인 | FIXED |
| CLAIM-005 | P2 | Compare | `app/app.py` | 효과를 사각지대 해소로 단정 | 인과적 과장 | FIXED |
| UI-001 | P2 | UI | `app/app.py` | 개발 Phase명이 사용자 문구에 잔존 | 제출 UI 혼선 | FIXED |
| TEST-001 | P2 | Test | `run_phase10_tests.py` | 삭제된 고정 benchmark 문구 요구 | 올바른 claim 수정 방해 | FIXED |

## 5. Known Bug A — is_unentered

- Current reproduction: 세 모델 각각 exclude OFF/ON AppTest 실행, 예외 0건.
- Root cause: 순수 Baseline scorer는 해당 컬럼을 생성하지 않으나 과거 UI 후단이 무조건 참조.
- Fix: 최신 앱의 Baseline 활성 결과에 기존 의미(`cat_store_count < 1`)로 schema를 보완하고 fallback mask를 사용한다.
- Regression: 숙박 Baseline OFF 150행, ON 127행, 0점포 23행 제외, Rank 1..127 확인.

## 6. Known Bug B — 유동인구 wording

| File | Text/Context | User Visible | Actual | Verdict | Action |
|---|---|---:|---|---|---|
| `explain.py:48` | 관내 지하철 일평균 유동인구 | Yes | 도시철도 승하차 | Invalid | 승하차 인원으로 수정 |
| `personalization.py` | 교통/유동인구 우선형 | Yes | 대중교통 접근성 | Invalid | 프리셋명 수정 |
| `README_JUDGE.md` | 청년 유동인구 | Yes | 주민등록 2030 타깃 | Invalid | 주민등록인구로 수정 |
| `MODEL_CARD.md` | 광역 유동인구 | Yes | 대중교통 승하차/접근 | Invalid | 관측 의미로 수정 |
| README/DATA_SOURCES | 통신사 유동·생활인구 미포함 | Yes | 미사용 데이터 고지 | Valid | 유지 |
| 테스트/docstring | 금지어 검사 문자열 | No | 회귀 검사 | Valid | 유지 |

실제 생성한 90개 설명에서 긍정적 `유동인구` 표현은 0건이다.

## 7. Additional Runtime Issues Found

추가 submission-blocking runtime issue는 발견되지 않았다. 현실적인 미진입 필터는 해당 업종의 0점포 행만 제외하므로 지원 업종에서 empty result가 발생하지 않았다.

## 8. Additional Claim Issues Found

비교 탭의 실제 비교 대상은 순수 Baseline이 아니라 0점포 보정이 적용된 도시철도 중심 개선 모델이었다. 표시명을 실행 branch와 일치시켰고, `사각지대 해소/정당한 평가`는 `도시철도 중심 평가 한계 보완/접근성 변화`로 제한했다.

## 9. Schema Audit

| Column | Integrated | Improved | Baseline(active) |
|---|---:|---:|---:|
| rank/adm_cd2/adm_nm/total_score | YES | YES | YES |
| 6 component scores | YES | YES | YES |
| cat_store_count/is_unentered/market_status | YES | YES | YES |
| subway_accessibility_score | YES | YES | NO (불필요) |
| bus_accessibility_score | YES | YES | NO (불필요) |
| bus observations | YES | YES | YES (참고 관측값) |

UI 필수 공통 13개 컬럼은 세 활성 branch 모두 존재한다. 모델 전용 점수 컬럼은 CSV에서 존재할 때만 포함된다.

## 10. UI Combination Audit

세 모델 × exclude ON/OFF를 실제 AppTest로 실행했다. 숙박 edge case 및 Integrated → Baseline → Improved → Baseline → Integrated 전환을 포함해 Streamlit exception 0건이었다. 6개 업종, 5개 타깃, 6개 프리셋과 custom normalization을 risk-based 조합으로 검사했다.

## 11. Explanation Grounding Audit

- 검증: 3 models × 6 scenarios × Top5 = 90
- Numeric mismatch: 0
- Unsupported feature/major hallucination: 0
- 승하차 데이터 `유동인구` 오표현: 0

## 12. CSV / Map / Session State Audit

세 모델 CSV는 150행(숙박 필터 ON은 127행), Rank·총점·6대 Component를 포함하며 UTF-8-SIG, NaN 0이다. 지도와 Top5는 모두 현재 `active_ranked`를 사용한다. 데이터 캐시는 파일 로드에만 적용되어 업종·타깃·모델 결과 cache leakage가 없었다.

## 13. Files Modified

| File | Before SHA-256 | After SHA-256 |
|---|---|---|
| app/app.py | `2c59c0eb...c21e5a0a` | `1302928c...acf5ef` |
| scoring.py | `e620cd83...b76d6e` | 동일 |
| improved.py | `93c277f7...8cd6f` | 동일 |
| transit_enhanced.py | `5fffab1c...680dda` | 동일 |
| explain.py | `794b44c9...539d4f` | `f0af3ae3...27712` |
| ranking.py | `a75c3079...8615b` | 동일 |
| personalization.py | `916630fa...67fd8` | `fc02c48a...d0ce2` |

추가 변경: `run_phase10_tests.py` stale assertion 교정, `run_phase15_hardening_tests.py` 신규, 제출 문서·manifest·checksums 동기화.

## 14. Regression Tests

- Phase 6: 10/10
- Phase 7: 12/12
- Phase 8: 10/10
- Phase 9: 10/10
- Phase 10: 10/10
- Phase 15: 12/12
- Total: 70/70 PASS (Phase 6~10 52 + Phase 14C 6 + Phase 15 12)

## 15. Representative Result Preservation

Integrated 카페+2030 기본 신암4동 77.75, 학원+10대 타깃집중 범어1동 84.47. Baseline 카페 77.93, 한식 71.54, 학원 80.16, 숙박 77.00을 모두 재현했다.

## 16. Browser QA

Playwright Chromium으로 1920×1080 및 1440×900에서 Header, Top1/Top5, 지도 iframe, 비교·금융·CSV 탭을 확인했다. Browser/page console exception은 0건이었다.

## 17. Clean Room

`/tmp/daegu_phase15_clean.VoGfos`에 최종 ZIP을 압축 해제했다. ZIP 내부 코드로 Phase 6~10 52/52, Phase 15 12/12, CHECKSUMS 55/55가 통과했고 AppTest 기동 및 Baseline+숙박+미진입 제외에서 예외 0건이었다.

## 18. Security Audit

최종 ZIP 검사 결과 Secret 0, API key 0, PII 0, Restricted data 0, `.env` 0, `.git` 0, `.venv` 0, `__pycache__` 0, 개인 절대경로 0이다. 비밀값이 없는 `.env.example`만 설정 예시로 포함했다. 참가신청서 PDF/HWP는 포함하지 않았다.

## 19. Final ZIP

- Filename: `말괄량이코물이_대구소상공인_AI_입지추천_제출코드_FINAL_v3.zip`
- 크기와 ZIP SHA-256은 ZIP 외부의 `submission/phase15_final_hardening_audit.md`에 기록한다(보고서 자체를 ZIP에 포함하는 해시 순환 방지).

## 20. Remaining Issues

Submission-blocking runtime/claim issue 없음.

## 21. Final Verdict

🟢 FINAL HARDENED ZIP READY
