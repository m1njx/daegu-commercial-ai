# Phase 19 Cross-Layer Consistency Audit

## 1. Executive Summary

코드, 실제 Streamlit UI, 설명 생성기, 제출 문서, 테스트, 스크린샷을 동일한 개념 기준으로 전수 대조했다. 확인된 정합성 오류는 모두 최소 수정했으며 추천 수식, 가중치, Feature Mart, 데이터 및 추천 결과는 변경하지 않았다.

최종 결과는 Python 3.10.21 Clean Room 기준 전체 103/103 PASS, Chromium 6개 데모 및 주요 컨트롤 PASS, 사용자 화면 오류·경고 0건이다.

## 2. XAI Branch Consistency

| UI 경로 | 통합 대중교통 | 도시철도 중심 개선 | 초기 기준선 |
|---|---|---|---|
| Top1 | enhanced | improved | baseline |
| Top2~5 설명 렌더 함수 | enhanced | improved | baseline |
| 상세 분석 | enhanced | improved | baseline |

`generate_active_explanation()`을 공통 선택 지점으로 두고 세 경로가 같은 모델 분기 정책을 사용하도록 교정했다. 현재 화면의 Top2~5 컴팩트 카드는 컴포넌트 점수 라벨을 표시하며, `render_sub_rank_card()`는 현재 호출되지 않는 보존 함수다. 해당 함수가 다시 사용되더라도 통합 모델에서 철도 전용 설명으로 빠지지 않도록 회귀 테스트로 고정했다.

18개 모델-시나리오의 Top5, 총 90개 설명을 생성해 빈 설명, 숫자 grounding 오류, 명백한 hallucination이 없음을 확인했다.

## 3. Competition Name

- Before: `2026 iM뱅크 데이터톤 출품작`
- After: `2026 AI Blockchain Challenge in Daegu 출품작`
- 사용자 UI, README, README_JUDGE, manifest에서 공식 명칭을 확인했다.
- `데이터톤`은 사용자 노출 위치 0건이며, Phase 19 부정 회귀 assertion의 금지 문자열 1건만 존재한다.

## 4. Model Comparison Label

- Before: `Baseline vs 통합교통 모델`
- Actual branch: `candidate="baseline", is_improved=True`인 도시철도 중심 개선 모델과 Candidate B 통합 대중교통 모델 비교
- After: `도시철도 중심 개선 모델 vs 통합 대중교통 모델`
- 탭, 본문, 심사 가이드, 최신 제출 스크린샷을 같은 명칭으로 통일했다.

## 5. Ranking Reproducibility

- Production sort keys: `[total_score, demand_score, target_fit_score, pop_total]`
- Old docs: `[total_score, demand_score, target_score, adm_cd2]`
- New docs: `[total_score, demand_score, target_fit_score, pop_total]`
- 6개 대표 시나리오 × 3개 모델, 총 18개 결과에서 복합 정렬키 중복: 0건

순위 코드는 변경하지 않았고 문서만 실제 구현에 맞췄다.

## 6. Target Option Consistency

실제 UI 옵션은 5개다.

1. `2030 청년 소비층 (20~39세)`
2. `전체 인구 (전연령)`
3. `10대 이하 (0~19세)`
4. `4050 중장년 구매력층 (40~59세)`
5. `60대 이상 시니어층`

README의 `6대 타깃` 주장을 `5개 타깃`으로 교정했고, README_JUDGE의 존재하지 않던 `10대 청소년층 (10~19세)`를 실제 UI 및 `pop_under20` 범위와 일치하는 `10대 이하 (0~19세)`로 교정했다.

## 7. Industry Option Consistency

실제 selector는 카페, 한식, 미용실, 학원, 종합소매, 숙박, 예술·스포츠의 7개 대표 업종과 `직접 입력`, 총 8개 값을 제공한다. README의 `6대 업종` 주장을 `7개 대표 업종 + 직접 입력`으로 교정했다.

## 8. Cross-Layer Concept Matrix

| Concept | Production / UI | README / Judge / Model Card / Reproducibility | 결과 |
|---|---|---|---|
| 공모전명 | 2026 AI Blockchain Challenge in Daegu | 동일 | 일치 |
| 팀명 | 말괄량이코물이 | 동일 | 일치 |
| 모델 | 통합 / 도시철도 중심 / 초기 기준선 | 동일 의미로 구분 | 일치 |
| 타깃 | 5개, 0~19세 포함 | 동일 | 일치 |
| 업종 | 7개 대표 + 직접 입력 | 동일 | 일치 |
| 프리셋 | 6개 + 사용자 직접 조정 | 동일 | 일치 |
| 순위 tie-break | total, demand, target_fit, pop_total | 동일 | 일치 |
| 설명 생성기 | enhanced / improved / baseline | 모델 의미와 동일 | 일치 |
| Target Fit | 기존 Production 구현 | 수식 의미 유지 | 일치 |
| 도시철도/버스 | Candidate B 70/30 | 동일 | 일치 |
| 정규화 | 기존 백분위 정규화 | 동일 | 일치 |

## 9. Files Modified

### Production/UI

- `app/app.py`: 설명 생성기 공통 분기, 공식 공모전명, 비교 탭명, 타깃 라벨, Streamlit 1.63 지도 iframe 호환 분기
- Before SHA-256: `d70a4be486d7336bd3a170e0a68902daa813783bcb1bc46076512d2da32644ea`
- After SHA-256: `2beb1e66a4f35d58f77ef57190748483f940c6887041308a38bfae0881fed0e2`

### Tests and tooling

- `scripts/run_phase19_crosslayer_consistency.py` 신규: 14개 회귀 테스트
- `scripts/run_phase10_tests.py`: 새 iframe 호환 분기 검증
- `scripts/run_phase17_python_compat_tests.py`: 최신 suite 합계 103 반영
- `scripts/verify_phase16_browser.py`, `scripts/verify_browser_ui.py`: 최신 탭/타깃 label 및 Streamlit tab locator 반영
- `scripts/capture_submission_screenshots.py`: URL/output 환경변수 지원 및 최신 role locator 반영

### Documentation/package metadata

- Root `README.md`
- Package `README.md`, `README_JUDGE.md`
- `docs/REPRODUCIBILITY.md`, `docs/TEST_REPORT.md`, `docs/MODEL_CARD.md`, `docs/PROJECT_STRUCTURE.md`
- `submission_manifest.json`, `CHECKSUMS.sha256`
- 제출 스크린샷 A~D 재캡처

## 10. Formula Preservation

다음 계산 모듈은 Phase 19 전후 SHA-256이 동일하다.

| File | SHA-256 | 변경 |
|---|---|---|
| scoring.py | `e620cd83cc769f4f1f0e575d076221ffc77eb4f9bd1320b06fbab9bfb4b76d6e` | 0 |
| personalization.py | `fc02c48a8d4ea071d42204f8e708abf16979e3e825e28fc1e4fbe09c9e0d0ce2` | 0 |
| ranking.py | `a75c3079b6b4a746714bcc391c3452fbd656c1d56251b71439d4053898f8615b` | 0 |
| feature_builder.py | `edab8ca489b19310b7deb91d6d76a7387a776226175fc45bb582accc4e93fc30` | 0 |
| bus_features.py | `f527063a9edb366305511b0f92d31cc11e48929b37dd8e8025880f66708e22f2` | 0 |
| improved.py | `c4723a71e0f4e1c0ce9cedcc82e7de1f193f54fa3b05f44e7eac55864a017b75` | 0 |
| transit_enhanced.py | `c16f3a86217bb5b6e30cc7bdaed5f30f0816b32a4c6bc83449bcc38eee981471` | 0 |
| explain.py | `1e7e5d6f35ba42ec944b33a0bd8f31e6a648d3ce6a1bc9e5ed575af2f0d9bca1` | 0 |

Candidate B 70/30, 6대 가중치, alpha 0.50, Feature Mart, 점수와 순위 결과는 변경하지 않았다.

## 11. Browser Acceptance

Python 3.10.21 Clean Room Streamlit을 Chromium에서 조작했다.

| Demo | Top1 | Score | 결과 |
|---|---|---:|---|
| 1 카페 + 2030 | 신암4동 | 77.75 | PASS |
| 2 한식 + 전체 | 상인1동 | 77.47 | PASS |
| 3 미용실 + 2030 | 칠성동 | 75.45 | PASS |
| 4 학원 + 10대 이하 | 범어1동 | 84.47 | PASS |
| 5 종합소매 + 전체 | 상인1동 | 72.22 | PASS |
| 6 숙박 + 2030 | 감삼동 | 75.82 | PASS |

3개 모델, 미진입 제외, 전체 업종/타깃/프리셋, 초기화, 5개 탭, 행정동 검색, 지도, CSV 다운로드를 확인했다. 브라우저 console error 0, page error 0, 사용자 노출 Streamlit warning/error 0이다. Streamlit 1.63에서 발생하던 `components.html` 폐기 예정 서버 로그도 `st.iframe` 우선 및 구버전 fallback으로 제거했다.

## 12. Existing Regression

| Suite | Result |
|---|---:|
| Phase 6 | 10/10 |
| Phase 7 | 12/12 |
| Phase 8 | 10/10 |
| Phase 9 | 10/10 |
| Phase 10 | 10/10 |
| Phase 14C | 6/6 |
| Phase 15 | 12/12 |
| Phase 16 | 12/12 |
| Phase 17 | 7/7 |

기존 합계: 89/89 PASS.

## 13. Phase19 Tests

`scripts/run_phase19_crosslayer_consistency.py`: 14/14 PASS.

설명 분기 3종, Top2~5 공통 selector, 공식 공모전명, 비교 branch/label, ranking docs, UI 옵션 수·라벨, 팀명, 모델 개념, 심사 가이드 label, 18개 모델-시나리오 정렬키 및 90개 설명을 검증한다.

## 14. Total Tests

89 + 14 = **103/103 PASS**.

## 15. Clean Room

- Path: `/tmp/daegu_phase19_release.D7vsHE/말괄량이코물이_대구소상공인_AI_입지추천`
- Interpreter: Python 3.10.21 독립 venv
- CHECKSUMS: 61/61 PASS
- compileall: PASS
- Full regression: 103/103 PASS
- Streamlit health: `ok`
- Chromium acceptance: 6/6 demos + full control audit PASS
- 원본 프로젝트 runtime 참조: 0

## 16. Security

- Secret/API key/private key pattern: 0
- `.env` 실제 파일: 0 (`.env.example` placeholder만 포함)
- 개인 절대경로: 0
- `.git`, `.venv`, `__pycache__`, `*.pyc`, `.DS_Store`, `__MACOSX`: 0
- HWPX, 내부 ZIP, IDE/AI history: 0
- PII 및 비공개 금융/통신 데이터: 0
- 포함 raw bus 데이터는 문서화된 공공 검증 데이터이며 runtime/출처 문서와 일치

## 17. Final ZIP

- Filename: `말괄량이코물이_대구소상공인_AI_입지추천_제출코드_FINAL_CONSISTENT.zip`
- Size: 16,401,233 bytes
- SHA-256: `974b86756f308b661f74e7d6f8609751578f8fffcbf9416bf31fafd5814ea81a`
- ZIP integrity: PASS

## 18. Remaining Issues

Submission-blocking cross-layer inconsistency 없음.

INFO: `render_sub_rank_card()`는 현재 UI 호출 경로가 없는 보존 함수다. 현재 보이는 Top2~5는 컴팩트 점수 카드이며, 함수 재사용 시 올바른 모델 설명기를 선택하도록 회귀 고정했다.

## 19. Final Verdict

🟢 CROSS-LAYER CONSISTENCY VERIFIED / FINAL READY
