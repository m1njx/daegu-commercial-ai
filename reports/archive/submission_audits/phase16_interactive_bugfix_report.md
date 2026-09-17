# Phase 16 Interactive Bug Fix Report

## 1. Executive Summary

실제 브라우저에서 재현된 Demo crash, Streamlit widget-state 경고, 한국어 조사 오류, 경쟁 문구 오타를 최소 수정했다. 추천 공식·가중치 벡터·Feature Mart·데이터·추천 결과는 변경하지 않았다. 기존 70개와 Phase 16 신규 12개는 총 82/82 PASS이며, 원본 프로젝트와 Clean Room에서 Chromium 전체 UI 검증을 각각 통과했다.

## 2. P0 Demo Crash

| Demo | Preset | Before | Root Cause | After |
|---|---|---|---|---|
| 1 카페+2030 | 기본 균형형 | `KeyError` | 장기 실행 중인 8502 프로세스가 과거 display label 기반 프리셋 dictionary를 메모리에 유지 | 신암4동 77.75, PASS |
| 2 한식+전체 | 배후 수요 집중형 | 실행되나 widget warning | widget default와 Session State 중복 | 상인1동 77.47, PASS |
| 3 미용실+2030 | 기본 균형형 | `KeyError` | Demo key와 프로세스 내 stale key 불일치 | 칠성동 75.45, PASS |
| 4 학원+10대 | 타깃 고객 집중형 | 실행되나 widget warning | widget default와 Session State 중복 | 범어1동 84.47, PASS |
| 5 종합소매+전체 | 기본 균형형 | `KeyError` | Demo key와 프로세스 내 stale key 불일치 | 상인1동 72.22, PASS |
| 6 숙박+2030 | 기본 균형형 | `KeyError` | Demo key와 프로세스 내 stale key 불일치 | 감삼동 75.82, PASS |

디스크의 canonical key와 Demo config는 `기본 균형형`으로 일치했다. 재발 방지를 위해 8502를 완전 재기동하고, Phase 16에서 6개 Demo preset이 실제 `WEIGHT_PRESETS`에 resolve되는지와 실제 callback 실행을 고정했다.

## 3. Session State Warning

- Before: `industry_choice` 등에 Session State 값을 미리 설정하면서 widget `index`도 동시에 전달해 Streamlit 경고 노출.
- Root cause: 동일 widget key에 두 개의 초기값 source가 존재.
- Fix: key가 Session State에 없을 때만 `index`를 전달. Demo callback이 설정한 widget state를 단일 source of truth로 사용.
- After: 6개 Demo 순차 전환, 업종·타깃·preset·model 전환에서 사용자 화면 warning 0.

## 4. Korean Particle Fix

- `타깃 고객층 집적 및 비중가` → `타깃 고객층의 집적도와 비중이`
- `일평균 승하차 인원가` → `일평균 승하차 규모가`
- `부설주차면 공급 여건가` → `부설주차면 공급 여건이`

설명 descriptor가 이미 조사를 포함하도록 정리하고 렌더러의 무조건적인 `가` 결합을 제거했다.

## 5. Competition Typo

- Before: `미크로 밀집 경쟁 주의`
- After: `근거리 동종업종 밀집 경쟁 주의`

반경 300m 동종 점포 수라는 실제 metric 의미를 그대로 반영했다.

## 6. Transit Terminology

- 과거 UI: `교통/유동인구 우선형 (도보 테이크아웃)`
- 현재 canonical UI: `대중교통 접근성 우선형 (도보 테이크아웃)`

도시철도·버스 승하차와 접근성 지표를 통신 유동인구로 표현하지 않는다. 새 브라우저 검증에서 positive misuse 0건이다.

## 7. Preset Key/Label Matrix

| Internal Key / Display Label | Weight Vector (수요/타깃/경쟁/교통/주차/특화) | Demo Reference |
|---|---|---|
| 기본 균형형 | 30/20/15/15/10/10 | 1, 3, 5, 6 |
| 배후 수요 집중형 (대형 매장/안정형) | 45/15/10/15/10/5 | 2 |
| 타깃 고객 집중형 (트렌디/특화 소비) | 15/45/10/15/5/10 | 4 |
| 대중교통 접근성 우선형 (도보 테이크아웃) | 20/15/10/35/10/10 | 없음 |
| 경쟁 회피 (블루오션 개척형) | 20/15/40/10/5/10 | 없음 |
| 주차/차량 방문 중심형 (외곽/대형 식당) | 20/10/10/10/40/10 | 없음 |

현재 구조에서는 canonical dictionary key가 UI label 역할도 한다. Phase 16은 모든 Demo reference가 canonical key로 resolve되는지 검사한다.

## 8. Files Modified

| File | Before SHA-256 | After SHA-256 | Change |
|---|---|---|---|
| `app/app.py` | `1302928ce4cd5e4da9645f36c64ab1251a57d97b88ca400575124b0dd7acf5ef` | `0ca3f8e070bfe739fa98177abc3f080820ab156f49592ef52196a332fbed1cc3` | widget state 초기화, 조사 문구 |
| `src/recommendation/explain.py` | `f0af3ae363834ccc72b71912f0380770a381b3efda92f466d7d422e8f3727712` | `1e7e5d6f35ba42ec944b33a0bd8f31e6a648d3ce6a1bc9e5ed575af2f0d9bca1` | 경쟁 문구 오타 |
| `src/recommendation/improved.py` | `93c277f7082bbdda4967cac5aab822f08d0ae53b35ab3fbc2f376d4cf448cd6f` | `c4723a71e0f4e1c0ce9cedcc82e7de1f193f54fa3b05f44e7eac55864a017b75` | 경쟁 문구 오타 |
| `src/recommendation/transit_enhanced.py` | `5fffab1c4646022b1d48c1506e5daa2e9fd9794447b5c79041db2a7830680dda` | `c16f3a86217bb5b6e30cc7bdaed5f30f0816b32a4c6bc83449bcc38eee981471` | 경쟁 문구 오타 |
| `scripts/run_phase16_interactive_regression.py` | 신규 | `2fa900c2bc2939b884c1ce7413bc79087bd87347c860a594b1f0537e16bf8ff8` | 12개 회귀 테스트 |
| `scripts/verify_phase16_browser.py` | 신규 | `a4ca36a73d74ac8aab31234e21dffa00e50e83f36994e2026213c604e2c049ee` | Chromium 전체 UI acceptance |

README, README_JUDGE, TEST_REPORT, REPRODUCIBILITY, PROJECT_STRUCTURE, MODEL_CARD, manifest 및 checksums도 82개 기준으로 동기화했다.

## 9. Production Formula Preservation

다음 수학 파일 hash는 Phase 15와 동일하다.

- `scoring.py`: `e620cd83...b76d6e`
- `ranking.py`: `a75c3079...8615b`
- `personalization.py`: `fc02c48a...d0ce2`

`improved.py`와 `transit_enhanced.py`의 변경은 사용자 설명 문자열 `미크로` 1건씩뿐이며 계산식 diff는 0이다. Candidate B 70/30, 6대 기본 가중치, alpha 0.50 및 ranking 공식은 불변이다.

## 10. Demo Browser Test

| Demo | Top1 | Score | Result |
|---|---|---:|---|
| 1 | 신암4동 | 77.75 | PASS |
| 2 | 상인1동 | 77.47 | PASS |
| 3 | 칠성동 | 75.45 | PASS |
| 4 | 범어1동 | 84.47 | PASS |
| 5 | 상인1동 | 72.22 | PASS |
| 6 | 감삼동 | 75.82 | PASS |

각 Demo에서 Top5, map iframe, explanation 렌더까지 확인했다.

## 11. Browser Warning/Error

Chromium에서 6개 Demo, 8개 업종 옵션, 5개 target, 7개 preset, 3개 model, 미진입 제외 ON/OFF, 5개 tab, 검색 및 CSV 다운로드를 조작했다.

- Streamlit exception: 0
- 사용자 노출 Streamlit warning: 0
- console/page error: 0
- 무한 rerun/stale state: 0

## 12. Explanation Regression

3 models × 6 scenarios × Top5 = 90/90 PASS.

- `비중가`, `인원가`, `여건가`, `미크로`: 0
- positive `유동인구`: 0
- rank/score mismatch: 0
- 주요 hallucination: 0

## 13. Existing Regression

- Phase 6: 10/10
- Phase 7: 12/12
- Phase 8: 10/10
- Phase 9: 10/10
- Phase 10: 10/10
- Phase 14C: 6/6
- Phase 15: 12/12
- 기존 합계: 70/70 PASS

## 14. Phase16 New Tests

`scripts/run_phase16_interactive_regression.py`: 12/12 PASS.

Demo preset resolution, 6개 Demo scoring, AppTest callback/warning, preset 벡터, 사용자 문구, 90개 explanation particle/grounding 및 UI template을 검사한다. 별도 `verify_phase16_browser.py`가 실제 Chromium 클릭을 담당한다.

## 15. Total Tests

기존 70 + Phase 16 신규 12 = **82/82 PASS**.

## 16. Clean Room

`FINAL_INTERACTIVE.zip`을 `/tmp/daegu_phase16_clean.BS07zO`에 해제했다.

- CHECKSUMS: 57/57 PASS
- 자동화 테스트: 82/82 PASS
- Streamlit 독립 기동: PASS (port 8518)
- 실제 Chromium 6 Demo + 전체 control audit: PASS
- 원본 프로젝트 절대경로 참조: 0

## 17. Security

새 ZIP에서 Secret, API key, PII, restricted data, `.env`, `.git`, `.venv`, cache, 개인 경로는 모두 0건이다. `.env.example`에는 placeholder만 있다. ZIP hygiene 위반 0건이다.

## 18. Final ZIP

- Filename: `말괄량이코물이_대구소상공인_AI_입지추천_제출코드_FINAL_INTERACTIVE.zip`
- Size: 16,488,200 bytes
- SHA-256: `13cd104ffda97581a8823eec853bf7f9b12599a4b3ba5022cf46171f3b284b70`

기존 `FINAL_AUDITED.zip`은 보존했다.

## 19. Remaining Issues

Submission-blocking runtime/UI issue 없음.

감사 호스트에 전역 설치된 `chardet 7.4.3` 관련 Requests 호환 경고는 터미널에만 발생한다. 제출 `requirements.txt`는 호환 범위 `chardet>=5.2,<6`을 명시하며 사용자 화면에는 노출되지 않는다.

## 20. Final Verdict

**🟢 FINAL INTERACTIVE ZIP READY**
