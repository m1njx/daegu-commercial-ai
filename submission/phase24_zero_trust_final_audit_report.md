# Phase 24 Zero-Trust Final Audit Report

## 1. Executive Verdict

Phase 24는 기존 Phase 보고서의 PASS 문구를 증거로 사용하지 않고 원천 파일, 재생성 데이터, 독립 계산 오라클, 실제 Chromium UI, PDF 렌더링 및 격리 환경을 다시 검사했다. 새로 확인된 결함은 세 건이었다.

1. **P1 재현성**: 전체 제출 스크립트가 직접 사용하는 `pypdf`, `reportlab`, `playwright`가 `requirements.txt`에 없었다.
2. **P1 계산 정합성**: 런타임 LQ가 행정동 업종비중을 소수 4자리로 먼저 반올림한 뒤 계산되어, Feature Mart 빌더의 반올림 전 비율 계산과 달랐다.
3. **P2 검증 스크립트**: Streamlit 1.64의 range input이 `aria-valuenow` 대신 `value`를 사용하여 브라우저 검증 스크립트가 UI는 정상인데도 실패했다.

세 문제는 재현 후 최소 수정했고 독립 회귀를 추가했다. 핵심 6대 가중치, Candidate B 70/30, alpha 의미, 경쟁 범위 및 순위 정렬 공식은 변경하지 않았다.

## 2. Audit Method

`DISCOVER → RAW DATA → CLEAN REBUILD → INDEPENDENT ORACLE → FUZZ → BROWSER → PDF → DEPENDENCY → SECURITY → PACKAGE` 순으로 수행했다. 기존 보고서 수치는 계산 결과의 source of truth로 사용하지 않았다.

## 3. Project Inventory

- 감사 시작 시 원본 작업 폴더: 파일 167개, 디렉터리 34개, 약 317.8 MB
- 주요 Python 파일: 51개
- 주요 데이터: CSV 23개, Parquet 6개, GeoJSON 1개, SHP 세트 1개
- 문서: Markdown 40개, PDF 2개
- 개발 이력 ZIP 5개는 원본 `submission/`에 보존되어 있으나 최종 코드 ZIP 내부에는 포함하지 않는다.
- 실제 엔트리포인트: `app/app.py`
- 활성 모델 코드: `src/recommendation/`
- 원천/파생 파이프라인: `scripts/build_feature_mart.py`, `src/features/bus_features.py`

## 4. Environment & Dependencies

- 호스트: macOS arm64
- 설치 확인: Python 3.10.21, 3.11.15, 3.14.5
- Python 3.10/3.11/3.14 `compileall app src scripts`: PASS
- 깨끗한 Python 3.11 venv에서 기존 requirements 설치 후 Phase22/PDF/브라우저 스크립트가 각각 `pypdf`, `reportlab`, `playwright` 누락으로 실패하는 것을 재현했다.
- 세 직접 의존성을 requirements에 추가했다. 브라우저 바이너리는 문서에 `python -m playwright install chromium` 별도 단계를 명시했다.
- `pip check`: PASS
- `pyflakes`: undefined name 또는 missing import 0건. 사용하지 않는 import 경고는 런타임 영향 없는 P3로 분류했다.

## 5. Raw Data Audit

| 데이터 | 독립 재계산 결과 |
|---|---:|
| 상가업소 | 118,357행, 고유 ID 118,357, 행정동 150, 대분류 10, 중분류 75, 좌표 결측 0 |
| 도시철도 | 39,856행, 94역, 2026년 1~7월 212일, 결측 0 |
| 주민등록 인구 | 대구 원본 152행, 출장소 2개 부모동 병합 후 150동, 총 2,347,389명 |
| 부설주차장 | 4,765개소, 247,329면, 유효 geometry 4,765 |
| 버스 위치 | 3,981 pole, 고유 정류소명 3,692 |
| 버스 이용량 | 고유 정류소명 3,666, 이름 매칭 3,624(98.85%), 이용량 커버리지 99.10% |

버스 미매칭 42개 이름의 이용량은 임의 위치에 배분하지 않는다. 이 제한은 데이터 문서에 유지한다.

## 6. Spatial Integrity

- 행정동 경계: EPSG:4326, 150개, `adm_cd2` 고유 150, invalid/empty geometry 0
- 공간 계산: EPSG:5179 투영
- 도시철도 94역 중 대구 행정동 내부 88역. 나머지 6역은 경산시 구간으로 대구 경계 밖이며 네트워크 지도에는 표시되나 대구 행정동 관내 승하차 집계에는 포함되지 않는다.
- 상가 좌표 결측 0, 주차 geometry 결측 0
- 버스 경계 인접점은 파이프라인의 최근접 행정동 처리 경로를 재검증했다.

## 7. Feature Mart Rebuild

최신 제출 ZIP만 `/tmp`에 독립 해제해 raw → Feature Mart와 raw bus → bus mart를 재실행했다.

- 동 마트: 150×47, 값 차이 0
- 동×대분류 마트: 1,454×29, 값 차이 0
- 점포 공간 마트: 118,357×39, 좌표 최대 차이 `1.63e-9`(부동소수 허용범위)
- 버스 동 마트: 150×11, 값 차이 0
- 버스 stop 마트: 3,981×21, 좌표 최대 차이 `1.40e-9`
- raw/processed 원본은 재생성용 `/tmp` 사본에서만 쓰였고 원본 작업 데이터는 변경하지 않았다.

## 8. Competition Scope Verification

음식점·학원·카페·한식·숙박에 대해 선택 업종 집합의 점포 좌표를 사용한 brute-force 거리행렬과 production cKDTree 결과를 10개 동 표본에서 대조했다. 반경 300m, 자기 자신 제외, 복수 중분류 union 규칙이 일치했다. 직접 입력 exact/부분 일치와 미지원 입력의 명시적 `ValueError`도 확인했다.

## 9. Industry Fit Verification

현행 Industry Fit은 `percentile(LQ)` 100%이며 전체 총점 가중치는 10%다. 과거 60/40 잔존 계산은 production에 없다.

Phase24 독립 계산에서 런타임이 `store_share_in_dong` 표시값을 4자리로 반올림한 다음 LQ를 계산하는 조기 반올림 결함을 찾았다. 수정 후:

`raw_share = category_count / total_stores`

`display_share = round(raw_share, 4)`

`LQ = round(raw_share / city_share, 3)`

로 분리했다. 7개 업종, 20개 이상 동 표본의 독립 분자·분모 계산과 일치한다.

## 10. Six Component Formula Audit

SciPy `rankdata(method="average")`로 production `pandas.rank`를 재사용하지 않는 독립 백분위 오라클을 구성했다. 6개 공식 데모×150동의 Demand, Target Fit, Competition, Accessibility, Parking, Industry Fit 및 Total Score 최대 절대차는 반올림 허용범위 0.011 이하였다.

## 11. Independent Score Reproduction

독립 오라클은 다음을 별도 계산했다.

- Demand: 인구 35%, 밀도 25%, 도시철도 승하차 20%, 총점포 20%
- Target Fit: 타깃 비중 60%, 절대인구 40%
- Competition: 점포당 타깃인구 50%, 선택 업종 300m 경쟁 역방향 50%
- Accessibility: 철도 70%, 버스 30%
- Parking: 300m 부설주차 50%, 점포당 30%, 동 총면수 20%
- Industry Fit: LQ 백분위 100%

## 12. Ranking & Tie-Break Audit

정렬은 `[total_score, demand_score, target_fit_score, pop_total]` 모두 내림차순이다. 순위는 필터 후 1부터 연속 재부여되며 TopN 0/음수는 `ValueError`다. 공식 시나리오에서 `adm_cd2` 고유, Rank 1~150 고유, 점수 범위 0~100을 확인했다.

## 13. Alpha Verification

`alpha=0.30/0.50/0.80`을 독립 실행했다. 해당 업종 점포 확인 지역의 경쟁점수는 alpha에 불변이고, 점포 미확인/최소 총점포 미달 지역만 단조 증가했다. 실제 UI의 모델 설명·비교 제목은 현재 slider 값을 동적으로 표시한다.

## 14. Transit Verification

- 도시철도와 버스 지표는 각각 백분위화한 뒤 70/30으로 결합한다.
- 버스 필수 피처가 없을 때 Candidate B는 중립 50으로 숨기지 않고 `ValueError`를 발생시킨다.
- 버스 matched 일평균 총량 `754,596.2688679246`은 matched raw volume `159,974,409 / 212`와 일치한다.

## 15. Six Demo Results

| 시나리오 | Top 1 | 최종 점수 |
|---|---|---:|
| 카페 + 2030 | 신암4동 | 77.75 |
| 한식 + 전체 | 상인1동 | 77.47 |
| 미용실 + 2030 | 칠성동 | 75.45 |
| 학원 + 10대 이하 | 범어1동 | 84.40 |
| 종합소매 + 전체 | 상인1동 | 72.25 |
| 숙박 + 2030 | 칠성동 | 75.90 |

LQ 조기 반올림 제거로 Top1 지역은 모두 유지됐다. 종합소매 Top1 점수만 72.22에서 72.25로 교정됐다.

## 16. Random Scenario Tests

고정 seed로 100개 업종·타깃·임의 비음수 가중치·alpha 조합을 실행했다. crash 0, NaN/Inf 0, 점수 범위 위반 0, 중복 행정동/순위 0이었다.

## 17. Explanation Grounding

3모델×6데모×Top5=90개 설명을 생성해 순위·점수·LQ·점포수·경쟁·교통·주차 행과 대조했다. LQ<1 집적 우위 단정, 0점포 업종 우위, 성공·보장·최적지·매출예측 표현은 0건이었다.

## 18. UI Static Audit

앱 사용자 문자열에서 구 팀명, 과거 공모전명, Plotly, 검증된 상권, 고정 alpha, 과거 데모 수치의 현재값 오표현을 검색했다. 사용자 노출 잔존 0건이다. 개발 이력 주석은 runtime 비노출로 구분했다.

## 19. Browser QA

- Chromium, 1920×1080 및 1440×900
- 6개 데모, 3개 모델, alpha 0.30/0.50/0.80, 5개 탭, CSV 다운로드
- console error 0, page error 0, Streamlit exception 0
- Streamlit 1.64 range input DOM 변경으로 기존 QA script가 실패한 것을 재현하고 `aria-valuenow`/`input.value` 양쪽을 지원하도록 수정했다.

## 20. CSV Audit

실제 브라우저 다운로드의 첫 3바이트 `EF BB BF`를 확인했다. 현재 모델·필터·연속 rank가 반영됐으며 한글 decoding 오류와 NaN은 없었다.

## 21. Documentation Audit

README, README_JUDGE, MODEL_CARD, DATA_SOURCES, REPRODUCIBILITY, TEST_REPORT, PROJECT_STRUCTURE 및 manifest를 코드·데이터와 대조했다. 테스트 합계는 Phase24 20개를 포함한 15개 스위트 184개로 동기화했다. 자동화 테스트가 사업적 유효성을 증명하지 않는다는 한계를 유지했다.

## 22. Proposal PDF Audit

- 실제 파일: `submission/documents/제안 요약서.pdf`
- 5페이지
- 최신 6개 데모 수치, 15개 스위트 184/184, MCDM 정의, 사업적 한계, Stage1/향후 Stage2~4 구분 반영
- Plotly 및 stale 점수 0건
- 코드 ZIP과 PDF는 별도 제출

## 23. PDF Visual QA

150dpi PNG로 5페이지 전부 렌더링해 잘림·겹침·깨진 한글·중복 제목·캡션 불일치·과거 스크린샷을 검사했다. 5/5 PASS. 3쪽 하단의 여백은 섹션 분리 결과이며 텍스트 누락이나 가림은 없다.

## 24. Data Source & License Audit

상가, 도시철도, 주민등록 인구, 부설주차장, 버스, 행정동 경계 출처를 DATA_SOURCES/LICENSES와 대조했다. 공개 원천 및 runtime/rebuild에 필요한 가공 데이터 외 카드 실매출·통신 생활인구·금융 내부 데이터·개인식별 데이터는 없다. 데이터별 이용조건이 동일하다고 일반화하지 않고 출처별 고지를 유지한다.

## 25. Test Quality Audit

테스트를 계산/데이터/런타임/문자열 회귀로 구분했다. 과거 suite 일부에는 문자열·snapshot 검사가 있으나 Phase24에서 핵심 계산을 production 함수와 독립인 brute-force·SciPy rank 오라클로 보강했다. `assert True`, silent skip, xfail, expected=actual 패턴은 0건이었다.

## 26. Security & PII Audit

최종 패키지 대상 파일에서 API key·secret·token·private key·개인 이메일·전화번호·개인 절대경로를 정규식 검사했다. `.env.example`은 placeholder만 포함한다. 개발 이력 archive에는 과거 로컬 링크가 있으나 최종 코드 ZIP 대상이 아니다.

## 27. Checksums & Package Audit

최종 코드 ZIP의 `CHECKSUMS.sha256` 등록 파일은 115개이며, checksum 파일 자체를 포함한 ZIP 전체 파일은 116개다. 클린룸에서 115개 항목을 전수 검증했으며 missing, extra, duplicate, mismatch는 모두 0건이다. ZIP 내부에는 PDF, 이전 ZIP, `.git`, `.venv`, cache, pyc, `.DS_Store`가 없다.

## 28. Clean Room Verification

최종 ZIP만 `/tmp/daegu_phase24_cleanroom`에 해제했다. checksum, compileall, `pip check`, 15개 suite 184/184, Streamlit 기동, 1920×1080 및 1440×900 Chromium 조작, CSV BOM을 재검증했다. 전체 suite는 역순으로도 184/184 통과했으며 테스트 전후 data hash가 일치해 입력 데이터 mutation은 0건이다. 클린룸 실행 중 원본 프로젝트 import/reference는 없었다.

## 29. Performance Sanity

Feature Mart 전량 재생성은 약 7.5초(호스트 기준)였다. Streamlit 최초 health와 브라우저 초기 렌더는 심사 시나리오의 60초 timeout 내 완료했다. 캐시 이후 데모 전환은 브라우저 검증의 1.2초 대기 범위에서 안정적으로 완료됐다.

## 30. Known Limitations

- 공공데이터 기반 MCDM 상대적 입지 적합도 모델
- 실제 매출·생존·폐업 ground truth 없음
- 창업 성공 확률 또는 매출 예측 모델 아님
- 임대료·권리금·실시간 공실 미포함
- 버스 이름 매칭 이용량 커버리지 99.10%; 미매칭은 임의 배분하지 않음
- 주차는 고객 이용량이 아니라 부설주차 공급 proxy
- 행정동 단위 결과이므로 현장 검토 필요
- 금융 로드맵 Stage2~4는 향후 확장

## 31. Newly Found Issues

| ID | Severity | Reproduction | Root cause | Fix | Status |
|---|---|---|---|---|---|
| P24-001 | P1 | clean venv에서 Phase22/PDF/browser import 실패 | 직접 의존성 3종 누락 | requirements와 재현성 단계 보완 | FIXED |
| P24-002 | P1 | 독립 LQ 오라클과 runtime 불일치 | 업종비중 4자리 조기 반올림 | raw share로 LQ 계산, 표시 share만 반올림 | FIXED |
| P24-003 | P2 | Streamlit 1.64 browser QA slider 값 읽기 실패 | DOM attribute 변경 | 구/신 DOM 양쪽 지원 | FIXED |

P24-002 영향: 6개 Top1 불변, Top5 6/6 불변, 900행 최대 총점 변화 0.13점, 최대 순위 변화 1계단. 상세 수치는 `reports/phase24_impact_analysis.json`에 기록했다.

## 32. Remaining Reproducible Issues

0건. 재현 가능한 코드·계산·데이터·UI·설명·문서·PDF·체크섬·패키지·보안 결함은 남아 있지 않다. 모델 자체의 범위와 데이터 한계는 30절에 별도 기재했다.

## 33. Final Submission Files

- 코드 ZIP: `말괄량이코물이_대구소상공인_AI_입지추천_제출코드_FINAL_ZERO_TRUST.zip`
- ZIP size: 38,639,131 bytes
- ZIP SHA-256: `8c26d0491cdbbaa3e7ae0589cd9389146a7c550bd3b80e7e7854ad3268b62dd8`
- Checksum registered files: 115
- ZIP total files: 116
- 제안 요약서 PDF: 코드 ZIP과 별도 제출
- PDF pages: 5
- PDF size: 9,328,400 bytes
- PDF SHA-256: `26934f4160882435be33333ba4e102722ec28458104a0cdecfe42bee4fc35ac0`

## 34. Final Verdict

**🟢 SUBMISSION READY**

Python 3.10.21 및 3.11.15에서 각각 184/184, 클린룸 역순 실행 184/184, 두 viewport 브라우저 QA, PDF 5/5 시각 QA, checksum 및 보안 검사를 통과했다. 새로 발견한 세 결함은 모두 재현·수정·회귀 고정했으며 남은 재현 가능 이슈는 0건이다.
