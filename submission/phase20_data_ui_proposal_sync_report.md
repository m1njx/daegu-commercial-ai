# Phase 20 Data/UI/Proposal Synchronization Report

## 1. Executive Verdict

🟢 **DATA/UI/DOCS SYNCHRONIZED — FINAL READY**

실제 원천 버스 데이터에서 원거리 동명이인 정류소 충돌을 재현하고, 정류소명 단독 그룹을 근접 공간 군집 방식으로 교정했습니다. 매칭된 원천 승하차 총량은 보존되었고 6개 대표 데모의 Top 1·점수·순위는 변하지 않았습니다. 상세 분석 150개 동 선택, 모델 비교 표기 순서, Demo 고급 상태 초기화, 필수 버스 피처 누락 처리, 랭킹 `top_n` 계약, 제안서 수치·기술 스택·화면을 동기화했습니다.

## 2. Bus Duplicate-Name Bug

### Before

`src/features/bus_features.py`는 이용량을 `정류소명`으로 합산한 뒤 같은 이름의 모든 물리 표지판 수로 나누었습니다. 이 방식은 상·하행 표지판 중복을 완화하지만, 같은 이름이면서 수 km 이상 떨어진 정류소까지 한 그룹으로 처리했습니다.

### Root Cause

이용량 원천에는 정류소 고유 ID·좌표·행정동이 없고 정류소명만 있습니다. 따라서 위치 원천과 연결할 때 별도 공간 구분 없이 정류소명만 사용하면 원거리 동명이인을 구별할 수 없습니다.

### Known examples and classification

| 정류소명 | 표지판 | 공간 군집 | 최대 거리 | 행정 구역 | 판정 |
|---|---:|---:|---:|---|---|
| 달산1리 | 7 | 4 | 23,047.0m | 소보면·우보면 | 원거리 동명이인, 분리 |
| 달산2리 | 7 | 4 | 21,350.0m | 소보면·우보면 | 원거리 동명이인, 분리 |
| 수서2리 | 5 | 3 | 12,806.8m | 군위읍·의흥면 | 원거리 동명이인, 분리 |
| 화계2리 | 2 | 1 | 18.6m | 경계 인접 | 근접 상·하행 가능성, 유지 |
| 화전리 | 2 | 1 | 20.5m | 산성면·우보면 경계 | 근접 상·하행 가능성, 유지 |

전체 중복 정류소명은 193개 그룹·482개 표지판이었습니다. 최근접 거리 중앙값은 12.1m, 95백분위는 194.2m였으며, 300m는 프로젝트가 이미 사용하는 정류소 접근권 반경이기도 합니다.

### Fix

같은 이름의 표지판을 EPSG:5179 좌표에서 300m 이내 연결요소로 군집화합니다. 이름 단위 이용량을 물리 군집 간 균등 배분한 뒤 각 군집의 표지판에 균등 배분합니다. 이로써 근접 상·하행 표지판 완화 의도는 유지하면서 원거리 동명이인을 분리합니다.

원천 이용량이 이름 단위이므로 개별 물리 정류소의 실제 이용량을 복원할 수는 없습니다. 문서에는 이 배분을 명시적 가정으로 기록했고, 개별 표지판 실측값이라고 주장하지 않습니다.

## 3. Bus Total Conservation

| 항목 | 값 |
|---|---:|
| 원천 전체 승하차 | 161,429,613건 |
| 위치 파일과 이름이 매칭된 승하차 | 159,974,409건 |
| 공간 매핑 커버리지 | 99.10% |
| 매칭분 기대 일평균 | 754,596.2688679246명/일 |
| 수정 후 표지판 합계 | 754,596.2688679246명/일 |
| 수정 후 150개 행정동 합계 | 754,596.2688679246명/일 |

배분 전 중간 반올림도 제거해 매칭된 원천 총량을 부동소수 허용오차 내에서 전량 보존했습니다.

## 4. Dong-level Impact

| 행정동 | 변경 전 | 변경 후 | 일평균 차이 |
|---|---:|---:|---:|
| 군위군 소보면 | 66.4900 | 66.6073 | +0.1173 |
| 군위군 우보면 | 57.8500 | 57.7700 | -0.0800 |
| 군위군 군위읍 | 428.1400 | 428.1887 | +0.0487 |
| 군위군 효령면 | 157.9900 | 157.9434 | -0.0466 |
| 군위군 의흥면 | 77.0500 | 77.0047 | -0.0453 |

가장 큰 변화는 군위군 소보면의 일평균 +0.1173명이었습니다. 그 외 소수 차이는 기존 소수 둘째 자리 중간 반올림을 제거한 영향입니다.

## 5. Demo Impact

| Demo | 최신 Top 1 | 점수 | 변경 영향 |
|---|---|---:|---|
| 카페 + 2030 + 기본 | 신암4동 | 77.75 | 없음 |
| 한식 + 전체 + 배후수요 | 상인1동 | 77.47 | 없음 |
| 미용실 + 2030 + 기본 | 칠성동 | 75.45 | 없음 |
| 학원 + 10대 이하 + 타깃집중 | 범어1동 | 84.47 | 없음 |
| 종합소매 + 전체 + 기본 | 상인1동 | 72.22 | 없음 |
| 숙박 + 2030 + 기본 | 감삼동 | 75.82 | 없음 |

도심 대표 동(신암4동·감삼동·상인1동·범어1동·칠성동)의 버스 접근성, 최종 점수, 순위는 변하지 않았습니다.

## 6. Tab2 Fix

상세 분석 selectbox를 Top 5 전용에서 선택 모델의 150개 행정동 전체로 확장했습니다. Top 5는 `Top N · 행정동명`으로 먼저 표시하고 나머지 동을 이어 제공합니다. 추천 결과에서 미진입 상권을 제외해도 상세 분석에서는 150개 전체 동을 선택할 수 있습니다. 실제 Chromium에서 Top 5 외 군위군 행정동의 6대 컴포넌트·관측표·설명·차트를 확인했습니다.

## 7. Tab3 Label Consistency

탭·본문·불릿·README_JUDGE·스크린샷 캡션 순서를 모두 다음으로 통일했습니다.

`통합 대중교통 모델(권장) vs 도시철도 중심 개선 모델`

## 8. Demo State Reset

Demo callback이 업종·타깃·프리셋·모델뿐 아니라 `alpha=0.50`, `미진입 완전 제외=OFF`를 함께 설정하도록 수정했습니다. 두 고급 위젯은 명시적 session-state key를 사용합니다. 실제 브라우저에서 임의 α·제외 상태를 만든 뒤 6개 Demo를 순차 선택해 공식 상태와 결과가 복원됨을 확인했습니다.

## 9. Bus Missing Feature Behavior

버스 가중치가 있는 Candidate A/B/C에서 필수 버스 컬럼 중 하나라도 없으면 누락 목록을 포함한 `ValueError`가 발생합니다. 철도 100% 비교 모델은 버스 점수가 계산에 사용되지 않으므로 기존 중립 표시값을 유지합니다. 알 수 없는 candidate 이름도 명시적 `ValueError`로 차단합니다.

## 10. Ranking Contract

`top_n=None`은 전체 결과를 반환하고, `top_n>=1`은 지정 수만 반환합니다. `top_n<=0`은 잘못된 호출로 `ValueError`를 발생시킵니다. 실제 프로덕션 호출은 `None` 또는 양수만 사용하므로 추천 공식·현재 순위에는 영향이 없습니다.

## 11. Proposal Score Corrections

제안 요약서의 과거 기준선 값과 초기 Phase 문구를 현재 Production 결과로 교체했습니다.

| 항목 | 변경 전 | 변경 후 |
|---|---:|---:|
| 카페 + 2030 | 77.93 | 77.75 |
| 학원 + 10대 이하 | 80.16 | 84.47 |
| 숙박 + 2030 | 77.00 | 75.82 |
| 자동 테스트 | Phase 6/7 중심 | 전체 117/117 |

## 12. Technology Stack Correction

실제 앱에서 사용하지 않는 `Plotly` 표기를 제안서에서 제거했습니다. 현재 표기는 Python, Pandas, NumPy, GeoPandas, Shapely, PyProj, Folium, Streamlit, CSV/Parquet입니다. `matplotlib`은 제출 앱 런타임이 아니라 저장소의 시각화 생성 스크립트에서 실제 import되므로 `requirements.txt`에서 유지했습니다.

## 13. Historical Docs Cleanup

과거 Phase 15 최종 ZIP 이름을 담은 감사 문서는 심사위원용 `docs/`에서 `reports/archive/submission_audits/`로 이동했습니다. 최종 코드 ZIP의 `docs/`에는 MODEL_CARD, DATA_SOURCES, REPRODUCIBILITY, TEST_REPORT, PROJECT_STRUCTURE만 포함했습니다.

## 14. Files Modified

핵심 파일 SHA-256:

| 파일 | 변경 전 | 변경 후 |
|---|---|---|
| app/app.py | `2beb1e66...fed0e2` | `273fd4a4...aad01` |
| src/features/bus_features.py | `f527063a...e22f2` | `7fa487c9...3a9380` |
| src/recommendation/transit_enhanced.py | `c16f3a86...81471` | `00401495...f77ea` |
| src/recommendation/ranking.py | `a75c3079...8615b` | `d654f0e7...b5a65` |
| src/recommendation/scoring.py | `e620cd83...fd0e2` | 동일 |
| src/recommendation/personalization.py | `fc02c48a...f30ce2` | 동일 |
| src/recommendation/feature_builder.py | `edab8ca4...fc30` | 동일 |

그 밖에 README, README_JUDGE, MODEL_CARD, DATA_SOURCES, REPRODUCIBILITY, TEST_REPORT, PROJECT_STRUCTURE, DATA README, manifest, Phase 17/19 stale 메타 테스트, Phase 20 테스트·브라우저 검증, 최신 스크린샷 5장, 제안 요약서 PDF를 동기화했습니다.

## 15. Processed Data Regenerated

- `data/processed/transit/bus/daegu_bus_stops_processed.parquet`
- `data/processed/transit/bus/daegu_bus_dong_features.parquet`
- `data/processed/transit/bus/daegu_bus_dong_features.csv`

Raw 버스 데이터는 변경하지 않았습니다.

## 16. Production Formula Preservation

Candidate B 70/30, 6대 가중치, alpha 의미, 컴포넌트 점수, 최종 점수 및 정렬 키는 변경하지 않았습니다. `scoring.py`, `personalization.py`, `feature_builder.py` 해시는 변경 전후 동일합니다. `ranking.py` 변경은 잘못된 `top_n<=0` 호출 계약에만 한정되며 정렬식은 동일합니다.

## 17. Tests

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
| Phase 19 | 14/14 |
| Phase 20 | 14/14 |
| **Total** | **117/117 PASS** |

## 18. Browser QA

원본과 Clean Room에서 각각 실제 Chromium으로 6개 Demo, arbitrary alpha/exclude → Demo reset, Top 5 외 행정동, 모델 비교, 지도, 로드맵, 데이터 탭, CSV를 검증했습니다.

- Demo: 6/6 PASS
- Console error: 0
- Page error: 0
- User-visible Streamlit warning: 0

## 19. Clean Room

`FINAL_DATAFIX.zip`을 `/tmp/daegu_phase20_cleanroom/`에 새로 해제했습니다. 원본 프로젝트를 참조하지 않고 체크섬 91개, compileall, 전체 117개 테스트, Streamlit 8520 기동, 실제 Chromium acceptance를 통과했습니다.

## 20. Security

최종 ZIP 검사 결과 Secret 0, API Key 0, PII 0, 제한 데이터 0, 개인 절대경로 0, `.git` 0, `.venv` 0, `__pycache__` 0, `.pyc` 0, HWPX 0, 내부 ZIP 0입니다. 포함 Raw 데이터는 공개 버스 정류소 위치·월별 이용량이며 재현 테스트에 필요한 범위입니다.

## 21. Final ZIP

- Filename: `말괄량이코물이_대구소상공인_AI_입지추천_제출코드_FINAL_DATAFIX.zip`
- Size: 23,435,744 bytes
- SHA-256: `c47b907b8994a80dbcca740752141d057213c44f52a59c6398b319efb378dcba`

## 22. Remaining Issues

Submission-blocking data/UI/document inconsistency 없음.

잔여 데이터 한계: 이용량 원천이 정류소명 단위라 원거리 동명이인의 군집별 실제 이용량은 식별할 수 없습니다. 현재 균등 배분 가정과 99.10% 공간 매핑 커버리지를 사용자·심사 문서에 명시했습니다.

## 23. Final Verdict

🟢 **DATA/UI/DOCS SYNCHRONIZED — FINAL READY**
