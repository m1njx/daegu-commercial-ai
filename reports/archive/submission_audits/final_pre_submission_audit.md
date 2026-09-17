# Final Pre-Submission Audit

감사일: 2026-09-09  
감사 대상: `말괄량이코물이_대구소상공인_AI_입지추천_제출코드_FINAL.zip`  
교정 산출물: `말괄량이코물이_대구소상공인_AI_입지추천_제출코드_FINAL_AUDITED.zip`

## 1. Executive Verdict

기능·모델·데이터에는 제출 차단 문제가 없었다. 다만 데이터 라이선스를 일괄 공공누리 제1유형으로 단정한 문구와 검증 범위를 넘어선 절대 표현 3건을 P2로 확인해 문서만 최소 교정했다. Production 코드, 수식, 가중치, Feature Mart 및 추천 결과 변경은 0건이다.

**최종 판정: 🟢 FIXED AND READY**

## 2. ZIP Integrity

- 기존 FINAL.zip: 16,481,554 bytes, SHA-256 `3d75e3279bc027dec054cf7e96edbc58c9e8cead43b5d032cf87091504a6377e`
- ZIP 무결성 검사: PASS
- 루트 폴더 한 개, 파일 56개, 심볼릭 링크 0개

## 3. Security

API key, token, password, private key, cloud credential, browser cookie 및 session file을 패턴·파일명으로 검사했다. 실제 비밀값 0건이다. `.env.example`에는 placeholder만 있다.

## 4. PII

개인 이름, 생년월일, 주민번호, 전화번호, 개인 이메일, 서명, 개인 주소 및 개인 로컬 경로 0건이다. 팀명과 프로젝트명만 포함한다.

## 5. Restricted Data

카드 실매출, 통신 생활인구 제한 원본, 금융·사내·개인식별 데이터 0건이다. 포함 데이터는 공개 원천 및 실행에 필요한 가공 산출물이다. 버스 공개 원천은 검증 재현을 위해 포함하며, Feature Mart는 원시 개인 단위 자료를 포함하지 않는다.

## 6. Hard-Coding Audit

| File | Line/Value | Classification | Action |
|---|---|---|---|
| `scripts/run_app.sh`, `run_app.bat` | 기본 포트 8501 | SAFE | Streamlit 기본 실행값, 외부 의존 아님 |
| 테스트·README | 77.75, 84.47, 77.93, 71.54, 80.16, 75.82 | SAFE | 회귀 fixture/재현 예시로만 사용 |
| 테스트·보고서 | Spearman 기준/관측값 | SAFE | 검증 기준이며 UI 결과는 동적 계산 |
| 전체 패키지 | `/Users/`, `/home/`, `C:\Users` | 해당 없음 | 개인 절대경로 0건 |

앱 런타임에 Top1, 점수 또는 Spearman을 고정하는 literal은 발견되지 않았다.

## 7. Dependency Audit

`requirements.txt`와 실제 import를 대조했다. pandas, numpy, geopandas, shapely, pyproj, scipy, matplotlib, pyarrow, requests, chardet, folium, streamlit이 포함되어 있으며 OS 전용 패키지는 없다. `pip check`는 정상이다. 감사 호스트의 별도 설치 상태(`chardet 7.4.3`)에서는 Requests 경고가 발생했지만 제출 요구사항은 `chardet>=5.2,<6`으로 호환 범위를 명시하므로 패키지 결함이 아니다.

## 8. Cross-Platform Audit

`run_app.sh`는 스크립트 기준 프로젝트 루트를 계산하고, `run_app.bat`는 `%~dp0`과 `cd /d`를 사용한다. 두 스크립트 모두 `app/app.py`를 올바르게 가리킨다. chmod를 전제로 하지 않는 직접 Python 실행 명령도 README에 있다. UTF-8 한글 경로는 ZIP 목록·해제·로드로 검증했다.

## 9. Path Portability

런타임 파일은 `Path(__file__)` 기반 프로젝트 루트에서 해석한다. 원본 프로젝트 밖 `/tmp`에 압축을 풀어 테스트와 앱 기동에 성공했으며 CWD·개인 경로 의존을 발견하지 못했다.

## 10. Runtime File Dependency

코드가 사용하는 CSV, Parquet, GeoJSON, 이미지가 ZIP에 존재하며 case-sensitive 이름이 일치한다. 외부 파일 및 심볼릭 링크 의존 0건이다.

## 11. Data Schema

- 행정동 Feature Mart: 150×47, 행정동 키 고유, NaN/Inf 0
- 업종 Feature Mart: 1,454×29, NaN/Inf 0
- 점포 공간 피처: 118,357×39, NaN/Inf 0
- 추천 점수: 2,250×42, NaN/Inf 0
- 버스 행정동 피처: 150×11, 행정동 키 고유, NaN/Inf 0
- 도시철도 좌표: 94×5, NaN/Inf 0
- GeoJSON: 150 geometry, empty/invalid/null 0, 행정동 키 중복 0

정류장 원천/가공 3,981행의 비필수 설명 필드에는 `영문명` 72, `동` 2, `경유노선` 43건의 결측이 있으나 좌표·승하차·행정동 집계 피처에는 전파되지 않고 런타임 계산에도 사용되지 않는다.

## 12. Model Branch Audit

통합 대중교통, 도시철도 개선, 기존 기준선 모델을 각각 실행했다. scoring, rank, 미진입 필터, explanation, CSV 및 공통 UI schema에서 branch-specific 오류 0건이다. Baseline의 `is_unentered` schema와 OFF 결과 보존도 통과했다.

## 13. UI Control Audit

Phase 15 AppTest/pairwise 검증으로 모델·업종·타깃·프리셋·custom weight·미진입 제외·demo·tabs 조합을 확인했다. Baseline/숙박/Baseline 제외 ON, Improved 제외 ON, Integrated 제외 ON 모두 정상이다.

## 14. Session/Cache

Integrated → Baseline → Improved → Baseline → Integrated 전환과 조건 변경 후 stale 결과 및 cache key 누락 0건이다. 캐시는 데이터 로딩에 사용되고 현재 선택 조건별 계산 결과를 잘못 재사용하지 않는다.

## 15. Edge Cases

숙박 0점포 23개 동, 지원 target 전체, 극단/0/음수 custom weight, 미지원 업종 예외를 검증했다. 제외 ON 결과는 127개이며 비어 있지 않아 Top1 `.iloc[0]` 경로가 안전하다.

## 16. NaN/Inf

세 모델의 Final Score, Rank 및 6대 Component 전수 NaN/+Inf/-Inf 0건이다. 0점포 나눗셈과 경쟁 보정도 회귀 테스트를 통과했다.

## 17. Ranking

점수 내림차순, 1부터 연속 순위, 중복 없는 rank, 필터 후 1..127 재랭킹을 확인했다. Top1/Top5/CSV/지도 데이터가 동일 결과를 사용한다.

## 18. Claim/Terminology

승하차를 긍정적으로 `유동인구`라 부르는 사용자 노출 경로 0건이다. 부정 disclaimer와 과거 버그 기록은 허용했다. 성공·매출·대출·제휴를 확정적으로 표현하는 런타임 claim 0건이다. 문서의 `완벽`, `100% 실측` 과장은 구체적 검증 범위로 교정했다.

## 19. Explanation Grounding

3모델 × 6시나리오 × Top5 = 90개 설명을 재검증했다. 숫자 mismatch 0, 존재하지 않는 변수 0, 주요 hallucination 0, causal overclaim 0이다.

## 20. Hard-Coded Runtime Values

지정된 점수와 Spearman 값은 테스트 fixture·README benchmark에만 있다. 현재 UI의 점수, 순위 및 Spearman은 선택 조건으로 계산된다.

## 21. CSV

세 모델 CSV가 UTF-8-SIG, 현재 모델/필터/rank 반영, 필수 6대 Component 포함, NaN 0으로 생성됨을 확인했다.

## 22. Map

모델별 score/rank/Top5/tooltip/choropleth가 같은 결과 DataFrame을 사용한다. 모델 전환 후 지도 state leakage 0건이다.

## 23. Browser QA

Playwright Chromium으로 1920×1080 및 1440×900을 검사했다. 헤더, Top1, Top5, Folium iframe, 모델 비교, 금융 로드맵, 데이터/다운로드 탭이 정상이며 console/page error 0건, 레이아웃 예외 0건이다.

## 24. README_JUDGE Reproduction

임의 `/tmp` 폴더에서 unzip → cd → 의존성/import 확인 → 테스트 → Streamlit 기동 절차를 수행했다. health endpoint가 `ok`를 반환했고 숨은 원본 프로젝트 참조는 없었다.

## 25. Tests

| Suite | Result |
|---|---:|
| Phase 6 | 10/10 |
| Phase 7 | 12/12 |
| Phase 8 | 10/10 |
| Phase 9 | 10/10 |
| Phase 10 | 10/10 |
| Phase 14C | 6/6 |
| Phase 15 | 12/12 |
| **Total** | **70/70 PASS** |

## 26. Test Quality

테스트에는 실제 DataFrame 계산, 파일 로딩, 150동 schema/rank 검증, 90개 explanation, AppTest 상태 전환 및 CSV 바이트 검사가 포함된다. 일부 source-string assertion은 단독 품질 증거가 아니라 UI 계약 회귀 guard로 쓰인다. hardcoded PASS나 무의미한 assertion은 발견하지 못했다. 브라우저 테스트는 별도 실사용 QA로 보완했다.

## 27. Documentation Consistency

manifest, README, README_JUDGE, TEST_REPORT, REPRODUCIBILITY, PROJECT_STRUCTURE가 모두 `52 + 6 + 12 = 70`, `70/70 PASS`와 일치한다. 전체를 64/64로 표기한 문구 0건이다.

## 28. License/Attribution

기존 문서는 공개 데이터 전체를 공공누리 제1유형으로 일괄 단정했다. 데이터별 상세 이용허락범위를 따르도록 교정하고, SGIS 경계는 SGIS 자료이용 동의·출처표시 조건을 별도로 명시했다. 확인되지 않은 라이선스를 새로 추정하지 않았다.

## 29. ZIP Hygiene

archive 내부 `.git`, `.venv`, `__pycache__`, `.pyc`, `.DS_Store`, `__MACOSX`, log, temp, backup, old ZIP, IDE 설정, AI history, prompt log, HWPX는 모두 0건이다.

## 30. Checksum

문서 및 manifest 교정 후 `CHECKSUMS.sha256`를 전수 재생성했다. 대상 55/55 PASS이며 manifest suite 합계도 70/70과 일치한다.

## 31. Clean Room

`FINAL_AUDITED.zip`을 `/tmp/daegu_audited_clean.eiuUq3`에 독립 해제했다. checksum 55/55, 테스트 70/70, Phase15 Baseline 필터, 데이터 로드, Streamlit port 8517 health `ok`를 확인했다. 원본 프로젝트 참조 0건이다.

## 32. Issues Found

| ID | Severity | File | Issue | Impact | Fix | Status |
|---|---|---|---|---|---|---|
| DOC-001 | P2 | `LICENSES.md`, `docs/DATA_SOURCES.md` | 서로 다른 공개 데이터 이용조건을 공공누리 제1유형으로 일괄 단정 | 재배포 근거 오해 가능 | 데이터별 조건 및 SGIS 조건 분리 표기 | FIXED |
| CLAIM-001 | P2 | `docs/DATA_SOURCES.md` | 99.10%에 `완벽히` 사용, `100% 실측치` 과대 표현 | 검증 범위 오인 | 관측 범위와 fallback 미사용 사실로 한정 | FIXED |
| CLAIM-002 | P2 | `docs/TEST_REPORT.md`, `docs/MODEL_CARD.md` | `모든`, `완벽 차단` 절대 표현 | 테스트 범위보다 강한 claim | 90개 검증 결과와 실제 보정 효과로 한정 | FIXED |
| ENV-001 | INFO | 감사 호스트 | 설치된 chardet 버전으로 Requests 경고 | 제출 requirements 재설치 시 해소 | 코드 변경 없음 | ACCEPTED |

P0/P1 문제는 발견되지 않았다.

## 33. Files Modified

- Production code/data: **0건**
- 문서: `LICENSES.md`, `docs/DATA_SOURCES.md`, `docs/MODEL_CARD.md`, `docs/TEST_REPORT.md`
- 패키징 메타데이터: `submission_manifest.json`, `CHECKSUMS.sha256`
- 외부 감사 보고서: `submission/final_pre_submission_audit.md`

핵심 Production hash는 기존 FINAL과 동일하다: `app.py` `1302928...acf5ef`, `scoring.py` `e620cd83...b76d6e`, `improved.py` `93c277f7...8cd6f`, `transit_enhanced.py` `5fffab1c...680dda`, `explain.py` `f0af3ae...27712`, `ranking.py` `a75c3079...8615b`, `personalization.py` `fc02c48a...d0ce2`.

## 34. Final ZIP

- 파일: `말괄량이코물이_대구소상공인_AI_입지추천_제출코드_FINAL_AUDITED.zip`
- 크기: 16,481,551 bytes
- SHA-256: `9ac23a821da40d06c918925856d61816dae238509adeae28dd2e2ebb62437d33`
- 기존 FINAL.zip: 보존

## 35. Remaining Risks

제출 차단 잔여 문제는 없다. 일반적 환경 위험은 심사 환경의 Python/네이티브 지리 패키지 설치 차이이며, 권장 Python 범위와 고정된 최소 버전 및 Windows/macOS/Linux 실행 절차로 완화했다. 원천 정류장 설명 필드의 일부 결측은 런타임 피처와 무관하다.

## 36. Final Verdict

**🟢 FIXED AND READY**

문서 정확성 P2 이슈만 최소 교정했으며 Production 동작과 추천 결과는 완전히 보존됐다. 제출 대상은 `FINAL_AUDITED.zip`이다.
