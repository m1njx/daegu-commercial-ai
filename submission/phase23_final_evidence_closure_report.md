# Phase 23 Final Evidence Closure Report

## 1. Executive Verdict

Phase 22 이후 남은 두 증빙 공백을 실제 데이터 계산과 실제 제출 PDF 실파일 검증으로 종결했습니다. 숙박 Top 1 변경은 경쟁점포 집계 범위 교정이 직접 원인이며, Industry Fit 단독 변경은 숙박 순위에 영향을 주지 않았습니다. 최종 PDF 5페이지는 runtime 수치·모델 정의·테스트 한계·금융 단계와 일치합니다.

**🟢 EVIDENCE VERIFIED / SUBMISSION READY**

## 2. Scope

- Phase 22 데이터에서 숙박+2030 네 가지 요인 조합 독립 재계산
- 실제 제출 파일 `submission/documents/제안 요약서.pdf` 직접 해시·텍스트·150dpi 렌더 검사
- PDF와 코드 ZIP의 별도 제출 구조 확인
- Phase 23 전용 14개 증빙 테스트 및 기존 회귀 재실행
- Production code/model unchanged; Phase 23 is evidence-only verification.

## 3. Lodging Top1 Change Investigation

### 3.1 Phase21 Result

기존 경쟁 범위와 기존 Industry Fit에서 감삼동 75.82가 1위, 칠성동 75.82가 2위였습니다. 동점 총점 이후 기존 정렬 기준에 의해 감삼동이 앞섰습니다.

### 3.2 Phase22 Result

선택 업종 전체 경쟁 범위와 LQ 백분위 Industry Fit에서 칠성동 75.90이 1위, 감삼동 75.87이 2위입니다.

### 3.3 Four-Way Factor Decomposition

| 조합 | 경쟁 범위 | Industry Fit | 감삼동 경쟁평균 / 경쟁점수 / 특화 / 총점 / 순위 | 칠성동 경쟁평균 / 경쟁점수 / 특화 / 총점 / 순위 |
| --- | --- | --- | --- | --- |
| A | 기존 중분류 평균 | 기존 60/40 | 1.5 / 62.75 / 36.24 / 75.82 / 1 | 5.0 / 39.76 / 50.34 / 75.82 / 2 |
| B | 선택 숙박업 전체 | 기존 60/40 | 1.5 / 63.08 / 36.24 / 75.87 / 2 | 5.1 / 40.26 / 50.34 / 75.90 / 1 |
| C | 기존 중분류 평균 | LQ 백분위 | 1.5 / 62.75 / 36.24 / 75.82 / 1 | 5.0 / 39.76 / 50.34 / 75.82 / 2 |
| D | 선택 숙박업 전체 | LQ 백분위 | 1.5 / 63.08 / 36.24 / 75.87 / 2 | 5.1 / 40.26 / 50.34 / 75.90 / 1 |

### 3.4 Root Cause

숙박+2030 데모의 Top 1이 감삼동에서 칠성동으로 변경된 직접 원인은 선택 업종 범위에 맞춘 경쟁점포 집계 방식 교정입니다. 감삼동 경쟁점수는 62.75→63.08, 칠성동은 39.76→40.26으로 바뀌었고, 최종 총점은 각각 75.87과 75.90이 됐습니다.

### 3.5 Industry Fit Contribution

A=C, B=D로 150동 전체 순위·점수가 동일했습니다. Industry Fit을 LQ 백분위 단일 지표로 단순화한 변경은 숙박 시나리오에 단독 영향을 주지 않았습니다.

## 4. Lodging Ranking Impact

- Phase 21 대비 Phase 22 숙박 150동 Spearman: **0.9996**
- Top 5 overlap: **5/5**
- Top 5 구성은 유지되고 1·2위 순서만 교체됐습니다.
- 감삼동–칠성동 최종 점수 차이: **0.03점**

## 5. Final Proposal PDF Identification

- Filename: `제안 요약서.pdf`
- Path: `submission/documents/제안 요약서.pdf`
- Size: **9,408,327 bytes**
- SHA-256: `a99d09a7f0c508e4e597d82a7e347d9ef0ed2f7080fd7aefcd2ca23381d9e655`
- Pages: **5**

## 6. PDF Runtime Consistency

PDF는 공공데이터 기반 MCDM 상대적 입지 적합도 모델, Industry Fit=LQ 백분위, 통합 대중교통 모델과 도시철도 중심 개선 모델, 성공률·매출·폐업 예측 모델이 아니라는 한계를 정확히 기술합니다.

| 데모 | PDF | Phase 22 runtime | 판정 |
| --- | --- | --- | --- |
| 카페 + 2030 | 신암4동 77.75 | 신암4동 77.75 | PASS |
| 한식 + 전체 | 상인1동 77.47 | 상인1동 77.47 | PASS |
| 미용실 + 2030 | 칠성동 75.45 | 칠성동 75.45 | PASS |
| 학원 + 10대 이하 | 범어1동 84.40 | 범어1동 84.40 | PASS |
| 종합소매 + 전체 | 상인1동 72.22 | 상인1동 72.22 | PASS |
| 숙박 + 2030 | 칠성동 75.90 | 칠성동 75.90 | PASS |

자동화 테스트 표기는 최종 14개 스위트 164/164로 동기화했고, 실제 사업 성과를 검증한 값이 아니라는 제한 문구를 유지했습니다. 금융 범위는 현재 Stage 1 입지 추천과 향후 Stage 2~4 연계를 구분합니다.

## 7. PDF Stale Value Scan

현재 결과로 오인될 수 있는 `감삼동 75.82`, `학원 84.47`, `카페 77.93`, `학원 80.16`, `숙박 77.00`, Plotly는 모두 0건입니다. 구 모델명, 데이터톤, 검증된 상권, 시너지 형성, 성공 가능성 과장 표현도 화면·본문에 없습니다.

## 8. PDF Visual QA

150dpi PNG로 전체 페이지를 다시 렌더링해 육안 검사했습니다.

| 페이지 | 핵심 내용 | 잘림/겹침 | 글꼴/가독성 | 캡션/화면 | 결과 |
| ---: | --- | --- | --- | --- | --- |
| 1 | 목적·해결책·데이터·기술 | 없음 | 정상 | 해당 없음 | PASS |
| 2 | 모델 정의·데모·한계 | 없음 | 정상 | 최신 수치 | PASS |
| 3 | 메인 추천 화면 | 없음 | 정상 | 화면·캡션 일치 | PASS |
| 4 | 지도·상세 분석 | 없음 | 정상 | 화면·캡션 일치 | PASS |
| 5 | 모델 비교·금융 로드맵 | 없음 | 정상 | 현재/향후 구분 | PASS |

중복 제목, 고립 heading, 깨진 한글, 흐린 핵심 수치, 최신 UI가 아닌 캡처는 0건입니다.

## 9. PDF / ZIP Submission Structure

제안 요약서 PDF는 대회 사이트에 코드 ZIP과 별도 제출합니다. README, README_JUDGE, PROJECT_STRUCTURE, manifest와 본 보고서가 동일하게 설명합니다. `FINAL_EVIDENCE_VERIFIED.zip` 내부 PDF는 0개입니다.

## 10. Phase23 Dedicated Tests

숙박 직접 원인, Industry Fit 단독 영향 0, 최종 runtime, PDF 존재·해시·페이지·최신값·stale값·Plotly·MCDM·테스트 한계·금융 단계, ZIP 내 PDF 0, 별도 제출 문서 정합성: **14/14 PASS**.

## 11. Full Regression Tests

- 기존 Phase 6~22: 150/150 PASS
- Phase 23: 14/14 PASS
- 합계: **164/164 PASS**
- 원본 작업 폴더와 독립 클린룸에서 PASS

## 12. Production Model Integrity

Phase 23에서 Production scoring, competition scope, Industry Fit, 가중치, α, 대중교통 통합, ranking, Feature Mart 및 추천 결과 변경은 **0건**입니다. 수정 범위는 증빙 테스트, 테스트 수 문서, PDF 테스트 수, 제출 구조 metadata와 보고서뿐입니다.

## 13. Final ZIP Status

- 기존 `FINAL_VALIDATED.zip`: 보존
- 새 제출 후보: `말괄량이코물이_대구소상공인_AI_입지추천_제출코드_FINAL_EVIDENCE_VERIFIED.zip`
- CHECKSUMS registered files: **112**
- ZIP total files: **113**
- Size: **38,718,199 bytes**
- SHA-256: `c2b631660302fc84dc8743fc3c1fc09eab416f64bfa551a5944956074058370b`

## 14. Remaining Evidence Gaps

**0건.**

## 15. Final Verdict

**🟢 EVIDENCE VERIFIED / SUBMISSION READY**
