# Phase 22 Final Semantic Integrity Report

## 1. Executive Verdict

외부 감사에서 제기된 경쟁점포 범위, α 표시, 모델 비교 의미, Industry Fit 중복, 사용자 설명 과장, 테스트 의미, Markdown 수식, 체크섬, PDF 및 ZIP 구조 문제를 실제 코드·데이터·브라우저·클린룸으로 재현하고 종결했습니다.

**🟢 FINAL VALIDATED / READY**

## 2. Audit Scope

`app/`, `src/`, `scripts/`, `docs/`, 런타임 데이터, 6개 공식 데모, 제안 요약서 5페이지, 코드 ZIP, 체크섬, 실제 Chromium 및 독립 클린룸을 검사했습니다. 자동화 테스트는 코드 실행, 데이터 무결성, 계산 재현성 및 UI·문서 정합성을 검증하며 실제 창업 성과, 매출, 생존율 또는 사업적 유효성을 검증한 결과가 아닙니다.

주요 변경 파일은 `app/app.py`, `src/recommendation/{feature_builder,scoring,improved,transit_enhanced,explain}.py`, README 2종, `docs/{MODEL_CARD,REPRODUCIBILITY,TEST_REPORT,PROJECT_STRUCTURE}.md`, 관련 회귀 테스트·브라우저 검사·영향 분석·패키징 스크립트, `submission_manifest.json`, 최신 스크린샷 5장, 제안 요약서 PDF입니다. 데이터 원본과 기존 `FINAL_CLOSED` ZIP은 변경하지 않았습니다.

## 3. Competition Scope Bug

### Reproduction

성내1동 음식점의 기존 `cat_avg_comp_300m`은 점포별 중분류 경쟁수를 평균하여 **82.8개**였습니다. 사용자가 선택한 음식업 전체 점포 집합으로 동일 반경을 계산하면 **422.2개**였습니다.

### Root Cause

사용자 선택 범위는 음식 대분류 전체였지만 경쟁점포는 각 기준 점포의 개별 중분류를 사용하여 UI의 “선택 업종 300m 경쟁”과 계산 범위가 달랐습니다.

### Fix

`cKDTree.query_ball_point`로 사용자 선택 업종 집합 전체의 300m 이웃 수를 계산하고 자기 자신을 제외했습니다. 음식점은 음식 대분류, 학원은 정의된 복수 중분류, 카페·한식 등은 선택 카테고리 범위, 직접 입력은 실제 해석된 업종 범위를 사용합니다.

### Before/After

성내1동 음식점은 경쟁점포 82.8→422.2, 경쟁점수 0.34→0.00, 총점 47.27→47.21, 순위 91→94였습니다.

### Ranking Impact

6개 데모 × 150동, 900행에서 총점 변화는 최소 -2.09, 최대 +1.06, 평균 -0.0006, 중앙값 0.00, 절대 변화 p95 0.301이었습니다. 순위 변화는 최소 -4, 최대 +8, 평균·중앙값 0, 절대 변화 p95 1이었습니다.

## 4. Alpha Synchronization

α는 계산 함수에 실제 전달되며 UI의 모델 설명, 비교 제목, 캡션에 `discount_factor_val`을 사용합니다. Chromium에서 0.30, 0.50, 0.80을 각각 조작해 계산과 표시가 일치함을 확인했습니다.

## 5. Model Comparison Semantics

비교표는 같은 α 조건의 “통합 대중교통 모델 vs 도시철도 중심 개선 모델” 비교로 명시했습니다. 할인 적용 전후 비교가 아니라는 설명도 화면에 추가했습니다.

## 6. Industry Fit Redesign

### Mathematical Redundancy

동일 업종에서 도시 전체 업종 비중은 상수이므로 LQ와 지역 업종 비중은 사실상 같은 순서 정보를 제공합니다.

| 업종 | Pearson | Spearman | 순위 불일치 행 | 최대 백분위 차이 |
| --- | ---: | ---: | ---: | ---: |
| 음식점 | 0.99999917 | 0.99999644 | 8 | 0.34 |
| 학원 | 0.99999993 | 1.00000000 | 0 | 0.00 |
| 카페 | 0.99999970 | 1.00000000 | 0 | 0.00 |
| 한식 | 0.99999967 | 0.99999822 | 4 | 0.34 |
| 미용실 | 0.99999970 | 1.00000000 | 0 | 0.00 |
| 숙박 | 1.00000000 | 1.00000000 | 0 | 0.00 |
| 종합소매 | 0.99999984 | 1.00000000 | 0 | 0.00 |

### New Definition

Industry Fit은 `100% × percentile(LQ)`로 단순화했습니다. 6대 컴포넌트에서 Industry Fit의 전체 가중치 10%는 유지했습니다.

### Ranking Impact

경쟁 범위 교정과 함께 계산한 통합 영향은 위 900행 통계 및 6개 데모 표에 반영했습니다.

## 7. Market Status Terminology

사용자 노출 상태를 `해당 업종 점포 확인 지역`, `해당 업종 점포가 적은 지역`, `해당 업종 점포 미확인 지역`으로 중립화했습니다. 점포 존재를 사업성 검증으로 표현하지 않습니다.

## 8. Explanation Claim Audit

LQ가 1 이상일 때만 대구 평균 대비 업종 비중 우위를 설명하며 “시너지 발생”을 단정하지 않습니다. 3개 모델 × 6개 데모 × Top 5 = 90건을 실제 생성해 과장 표현, LQ<1 집적 단정, 0점포 모순, 오래된 시장 상태 표현 0건을 확인했습니다.

## 9. Automated Test Interpretation

150/150 PASS는 코드 실행, 데이터 무결성, 계산 재현성, UI·문서 정합성의 회귀 검증 결과입니다. 창업 성공 확률, 매출 정확도 또는 사업적 타당성 검증이 아닙니다. 모델 간 Spearman 역시 행정동 순위 유사도이며 사업적 정확도를 뜻하지 않습니다.

## 10. Markdown Math Fix

README, 심사위원 가이드, MODEL_CARD, TEST_REPORT, REPRODUCIBILITY의 `\rho`, `\alpha`, `\sim`, `\to` 표기를 실제 Markdown 기준 단일 백슬래시로 검증했습니다.

## 11. Checksums Audit

`CHECKSUMS.sha256`를 최종 패키지 파일에서 다시 생성했습니다. 등록 111개 전부 검증됐고, 체크섬 파일 자체를 포함한 ZIP 파일은 112개입니다. 미등록·누락 파일은 0개입니다.

## 12. Proposal PDF Update

Phase 22 공식, 6개 데모, 150/150의 제한된 의미, 최신 화면 5장, 실제 기술 스택 및 MCDM 한계를 반영했습니다. Plotly·과거 점수·과거 모델명은 제거했습니다.

## 13. PDF Packaging Decision

대회 제출 구조에 따라 제안 요약서 PDF는 코드 ZIP과 별도 제출합니다. 따라서 코드 ZIP 내부 PDF는 0개이며 README와 PROJECT_STRUCTURE도 같은 구조를 설명합니다.

## 14. Six Demo Results

| 데모 | Phase 21 Top 1 | 이전 점수 | Phase 22 Top 1 | 최종 점수 | 순위 Spearman | Top 5 일치 |
| --- | --- | ---: | --- | ---: | ---: | ---: |
| 카페 + 2030 | 신암4동 | 77.75 | 신암4동 | 77.75 | 1.0000 | 5/5 |
| 한식 + 전체 | 상인1동 | 77.47 | 상인1동 | 77.47 | 1.0000 | 5/5 |
| 미용실 + 2030 | 칠성동 | 75.45 | 칠성동 | 75.45 | 1.0000 | 5/5 |
| 학원 + 10대 이하 | 범어1동 | 84.47 | 범어1동 | 84.40 | 0.9997 | 5/5 |
| 종합소매 + 전체 | 상인1동 | 72.22 | 상인1동 | 72.22 | 1.0000 | 5/5 |
| 숙박 + 2030 | 감삼동 | 75.82 | 칠성동 | 75.90 | 0.9996 | 5/5 |

## 15. 150-Dong Impact Analysis

| 순서 | 시나리오 | 행정동 | 이전 순위 | 최종 순위 | 순위 변화 | 총점 변화 |
| ---: | --- | --- | ---: | ---: | ---: | ---: |
| 1 | 숙박 | 복현2동 | 27 | 35 | +8 | -2.09 |
| 2 | 숙박 | 방촌동 | 97 | 101 | +4 | -1.33 |
| 3 | 학원 | 삼덕동 | 101 | 97 | -4 | +0.51 |
| 4 | 숙박 | 대봉2동 | 83 | 86 | +3 | -0.33 |
| 5 | 학원 | 상인2동 | 79 | 82 | +3 | -0.38 |
| 6 | 학원 | 신암5동 | 98 | 101 | +3 | -0.37 |
| 7 | 숙박 | 이곡2동 | 60 | 63 | +3 | -0.70 |
| 8 | 숙박 | 본동 | 85 | 83 | -2 | +0.20 |
| 9 | 학원 | 성당동 | 62 | 64 | +2 | -0.15 |
| 10 | 숙박 | 산격4동 | 122 | 124 | +2 | -0.75 |

## 16. Browser QA

최신 원본 서버와 ZIP 클린룸 서버 양쪽에서 Chromium으로 6개 데모, 세 모델, α 0.30/0.50/0.80, exclude 상태, 추천·상세·모델비교·로드맵·데이터 탭, CSV 다운로드를 조작했습니다. 콘솔 오류 0, 페이지 오류 0, 사용자 노출 개발 경고 0, CSV BOM `EF BB BF`를 확인했습니다.

## 17. Explanation Grounding

90/90 실제 설명 생성 PASS. 숫자 생성 오류, 오래된 공식·경쟁 정의, 시장 상태 과장, LQ<1 집적 단정, α 불일치 0건입니다.

## 18. Existing Regression Tests

Phase 6~21의 기존 132개 테스트를 원본과 클린룸에서 모두 통과했습니다.

## 19. Phase22 Dedicated Tests

경쟁 범위, 직접 입력, α, 비교 의미, Industry Fit, 설명 가드, 시장 상태, 테스트·Spearman 한계, Markdown, 체크섬, PDF, ZIP, 과장 표현을 다루는 18/18 PASS입니다.

## 20. Total Test Count

13개 스위트, 총 **150/150 PASS**입니다.

## 21. PDF Visual QA

최종 5페이지를 130dpi PNG로 렌더링하여 전 페이지를 육안 검사했습니다. 잘림 0, 겹침 0, 캡션 가림 0, 깨진 한글 0, 중복 heading 0, 페이지 분리 오류 0입니다.

## 22. Clean Room Verification

`/tmp/daegu_phase22_cleanroom`에 최종 ZIP을 독립 해제했습니다. 체크섬 111/111, compileall, 150/150 테스트, Streamlit 8522 health/startup, Chromium 브라우저 acceptance를 통과했으며 원본 경로 참조는 0건입니다.

## 23. Security/Hygiene

최종 ZIP에서 API key·secret·PII·개인 절대경로·`.env`·`.git`·`.venv`·`__pycache__`·`.pyc`·`.DS_Store`·중첩 ZIP·PDF는 모두 0건입니다. 포함 raw 파일은 문서화된 공개데이터 재현 자료이며 제한 데이터는 포함하지 않았습니다.

## 24. Final ZIP

- Filename: `말괄량이코물이_대구소상공인_AI_입지추천_제출코드_FINAL_VALIDATED.zip`
- Checksum registered files: 111
- ZIP total files: 112
- Size: 38,714,076 bytes
- SHA-256: `afbd74cd0019a07db6b699199c16e9221e9fe749f9c1b07af8079b4dabace99d`

## 25. Known Limitations

- 공공데이터 기반 MCDM 상대적 입지 적합도 모델입니다.
- 실제 매출·창업 성공·폐업 ground truth가 없어 성공 확률 모델이 아닙니다.
- 임대료·권리금·실시간 공실·상권 경계의 현장 상황은 포함하지 않습니다.
- 결과는 후보지 비교 자료이며 수요·비용·인허가·현장 조건을 별도로 확인해야 합니다.
- 금융 로드맵 2~4단계는 향후 확장이고 현재 구현은 AI 입지 추천 중심입니다.

## 26. Remaining Reproducible Issues

**0건.** 글로벌 개발 환경에서 보이는 선택적 라이브러리 경고는 제출 requirements의 `chardet<6` 계약과 `pip check`에서 해소되며 앱·테스트 결과에 영향을 주지 않습니다.

## 27. Final Verdict

**🟢 FINAL VALIDATED / READY**
