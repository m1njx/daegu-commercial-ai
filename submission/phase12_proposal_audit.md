# Phase 12 Proposal Grounding & Claim Audit Report

**문서 대상**: `submission/phase12_proposal_draft.md`  
**평가 대회**: 2026 AI Blockchain Challenge in Daegu (소상공인·골목상권 디지털 금융)  
**작성 팀명**: 상권ON AI  
**기준 일자**: 2026-09-09  
**감사 상태**: 100% COMPLETE (ZERO HALLUCINATIONS, STRICT FEATURE FREEZE)

---

## 1. 개요 및 감사 목적

본 감사는 2026 AI Blockchain Challenge in Daegu 공모전 1차 서면 평가용 약 5페이지 제안서 초안(`submission/phase12_proposal_draft.md`)에 기술된 모든 정량적 수치, 알고리즘 구현 현황, 데이터 소스, 스크린샷 일치성, 그리고 향후 비즈니스 확장 주장을 실제 프로젝트 코드(`app/app.py`, `src/`), 통합 Feature Mart(`data/processed/`), 원천 데이터(`data/raw/`), 그리고 이전 Phase(Phase 6~11) 검증 보고서와 1:1 대조하여 무결성을 최종 보증하기 위해 수행되었습니다.

---

## 2. 검증된 정량적 수치 (Numeric Grounding Audit)

제안서 본문에 등장하는 총 31개 주요 정량 수치에 대해 100% 실측치 검증을 완료하였습니다. (미검증 수치 0건)

| No. | 지표 / 수치 | 제안서 본문 기술 내용 | 검증 근거 파일 및 코드 위치 | 검증 결과 |
| :---: | :--- | :--- | :--- | :---: |
| 1 | **150개** | 대구광역시 전체 분석 대상 행정동 수 | `data/processed/feature_mart/commercial_feature_mart_dong.csv` (len=150) | **PASS** |
| 2 | **118,357개** | 대구시 전체 소상공인 상가업소 점포 수 | `data/raw/commercial/.../소상공인시장진흥공단_상가업소정보_대구_20260907.csv` | **PASS** |
| 3 | **2,347,389명** | 대구시 150개 행정동 총 주민등록 인구수 | `data/processed/feature_mart/commercial_feature_mart_dong.csv` (`pop_total.sum()`) | **PASS** |
| 4 | **94개** | 대구 도시철도 1·2·3호선 전체 역사 수 | `data/processed/transit/대구도시철도_역별_위경도좌표.csv` (94행) | **PASS** |
| 5 | **3,981개** | 대구 시내버스 전체 정류소 위치 개수 | `data/raw/bus/대구광역시_시내버스정류소위치정보_20260731.csv` (3,981행) | **PASS** |
| 6 | **3,666개** | 버스 승하차 데이터 고유 정류소명 수 | `reports/phase8_bus_integration_report.md` Section 3.1 | **PASS** |
| 7 | **3,624개** | 명칭 정규화 후 1:1 완전 일치 정류소 수 | `reports/phase8_bus_integration_report.md` Section 3.1 | **PASS** |
| 8 | **98.85%** | 정류소명 기준 매칭 성공률 | $3,624 / 3,666 = 98.854\%$ (`reports/phase8_bus_integration_report.md`) | **PASS** |
| 9 | **99.10%** | 승하차량 기준 버스 데이터 커버리지 | `reports/phase8_bus_integration_report.md` Section 3.1 | **PASS** |
| 10 | **3,976개** | 행정동 Polygon 내부 직접 매핑 정류소 | `reports/phase8_bus_integration_report.md` Section 3.2 | **PASS** |
| 11 | **5개** | 시 경계 인접 최근접 행정동 보정 정류소 | $3,981 - 3,976 = 5$ (`reports/phase8_bus_integration_report.md`) | **PASS** |
| 12 | **4,765개소** | 대구광역시 관내 부설주차장 수 | `data/raw/parking/대구광역시_부설주차장/대구부설주차장정보.shp` (4,765 features) | **PASS** |
| 13 | **247,329면** | 대구 관내 부설주차장 총 주차면수 | `data/processed/feature_mart/commercial_feature_mart_dong.csv` (`dong_total_parking_capacity.sum()`) | **PASS** |
| 14 | **1,491.39 km²** | 군위군 편입 후 대구광역시 전체 면적 | `reports/phase4_feature_mart_report.md` Section 3.1 (150개 동 면적 합계) | **PASS** |
| 15 | **59개 / 91개** | 도시철도 역 보유 행정동 / 미보유 행정동 | `commercial_feature_mart_dong.csv` (`dong_station_count > 0`: 59, `== 0`: 91) | **PASS** |
| 16 | **70% / 30%** | 대중교통 모델 지하철/버스 결합 가중치 | `src/recommendation/transit_enhanced.py` (`SUBWAY_WEIGHT=0.70, BUS_WEIGHT=0.30`) | **PASS** |
| 17 | **30/20/15/15/10/10** | 기본 6대 입지 컴포넌트 가중치 (%) | `src/recommendation/scoring.py` (`BASELINE_WEIGHTS`) | **PASS** |
| 18 | **0.9894 ~ 0.9943** | 6개 시나리오 Spearman 순위 상관계수 | `reports/phase8_bus_integration_report.md` Section 5.1 | **PASS** |
| 19 | **0.9924** | 한식 시나리오 실시간 Spearman $\rho$ | `submission/screenshots/04_model_comparison.png` (Screenshot D 상단 카드) | **PASS** |
| 20 | **33.41 $\rightarrow$ 37.22** | 비역세권 91개 동 평균 접근성 점수 변화 | `reports/phase8_bus_integration_report.md` Section 5.2 | **PASS** |
| 21 | **+3.81점** | 비역세권 91개 동 평균 접근성 보정폭 | $37.22 - 33.41 = +3.81$ (`reports/phase8_bus_integration_report.md`) | **PASS** |
| 22 | **+3.86점** | 한식 시나리오 비역세권 점수 개선폭 | `submission/screenshots/04_model_comparison.png` (Screenshot D 메트릭) | **PASS** |
| 23 | **77.75점** | 시나리오 1 추천 1위 신암4동 종합 점수 | `submission/screenshots/01_main_recommendation.png` (Screenshot A) | **PASS** |
| 24 | **84.47점** | 시나리오 4 추천 1위 범어1동 종합 점수 | `submission/screenshots/03_explainable_analysis.png` (Screenshot C) | **PASS** |
| 25 | **77.47점** | 시나리오 2 추천 1위 상인1동 종합 점수 | `submission/screenshots/04_model_comparison.png` (Screenshot D) | **PASS** |
| 26 | **103개소** | 범어1동 학원 점포 수 (관측 실측치) | `submission/screenshots/03_explainable_analysis.png` 정량 데이터 표 | **PASS** |
| 27 | **24.3% / 18.2%** | 범어1동 10대 인구 비율 / 대구 전체 평균 | `submission/screenshots/03_explainable_analysis.png` 정량 데이터 표 | **PASS** |
| 28 | **210m** | 범어1동 최근접 도시철도역 거리 | `submission/screenshots/03_explainable_analysis.png` 정량 데이터 표 | **PASS** |
| 29 | **18개소 / 4,797건**| 범어1동 버스 정류소 수 / 일일 버스 승하차 | `submission/screenshots/03_explainable_analysis.png` 정량 데이터 표 | **PASS** |
| 30 | **52/52** | 자동 회귀 테스트 통과 수 (Phase 6~10) | `scripts/run_phase10_tests.py` (Phase 6:10, 7:12, 8:10, 9:10, 10:10) | **PASS** |
| 31 | **30/30** | 추천 근거 Grounding 감사 통과 수 | Phase 10 최종 검증 보고서 Section 3 | **PASS** |

---

## 3. 기능 구현 상태 감사 (Claim Classification Audit)

제안서 본문에 기술된 기능 및 기술적 주장을 [현재 구현 완료], [실제 데이터 검증], [향후 확장 로드맵]으로 명확히 분류하여 심사위원의 오해 소지를 원천 차단하였습니다.

### 3.1 현재 구현 완료 기능 (Current Implementation Claims)
1. **대구 150개 행정동 분석**: 대구광역시 전역 150개 행정동(군위군 8개 읍·면 포함)을 동등하게 분석 및 스코어링.
2. **10개 소상공인 대분류 업종 선택**: 소상공인 표준 산업분류(음식, 소매, 교육/학원 등 10종) 지원.
3. **5개 목표 고객 연령대 선택**: 2030, 4050, 60대이상, 10대, 전체 연령대 타깃팅 지원.
4. **개인화 가중치 조정 및 6대 프리셋**: 기본 균형형, 타깃고객 집중형 등 6종 프리셋 및 Simplex 100% 정규화 슬라이더 제공.
5. **공공데이터 통합 Feature Mart 연계**: 11.8만 점포, 235만 인구, 94개 지하철역, 3,981개 버스 정류소, 4,765개 주차장 통합.
6. **6대 입지 적합도 다기준 평가 (MCDM)**: 배후수요, 타깃적합, 경쟁완화, 교통접근성, 주차편의, 업종특화 백분위 산출.
7. **Top 5 최적 입지 추천**: 종합 점수 기준 상위 5개 행정동 도출 및 실시간 랭킹 산정.
8. **Folium GIS 인터랙티브 공간 시각화**: 행정동 단계구분도 및 1~5위 추천 마커 핀 제공.
9. **설명 가능한 AI(XAI) 다차원 진단**: 6대 컴포넌트 분해 바 차트, 취약 항목 경고, 10개 실측치 정량 데이터 표 제공.
10. **도시철도(70%) + 시내버스(30%) 통합 대중교통 모델 (Candidate B)**: 기본 모델로 내장되어 비역세권 생활상권 접근성 정밀 반영.
11. **모델 비교 분석 기능**: 기존 단독 모델(Baseline) 대비 실시간 순위 변동 및 Spearman $\rho$ 계측.
12. **CSV 내보내기 및 웹 대시보드 프로토타입**: Streamlit 기반 대화형 웹 서비스 구현 완료.

### 3.2 실제 데이터 검증 결과 (Empirical Verification Claims)
1. **순위 안정성 보존**: 6개 대표 시나리오에서 Spearman $\rho = 0.9894 \sim 0.9943$, 실시간 측정값 $0.9924$ 입증.
2. **비역세권 구제 실증**: 도시철도 미경유 91개 동 평균 접근성 $+3.81$점 향상 실측.
3. **품질 무결성**: 52개 자동 테스트 100% PASS, 브라우저 QA 통과, 추천 근거 30/30 Grounding 확인.

### 3.3 향후 확장 로드맵 (Future Roadmap Claims) — 현재 미구현 명시
1. **2단계 창업 자금계획 지원**: 업종별 평균 점포 면적 기반 초기 창업비용(인테리어, 보증금 등) 추산 가이드 제공 계획.
2. **3단계 정책자금 정보 안내 및 상담 연계**: 소진공, 대구신보 등 공공 정책자금 지원 요건 안내 및 신청 채널 연계 계획.
3. **4단계 금융 API 활용 및 iM뱅크 제휴 금융상담 연계**: 오픈 API 활용 가능성 검토 및 iM뱅크 지점망 연계 금융상담 접점 구축 계획 (현재 연동 완료 아님을 명확히 명시).
4. **상용 빅데이터 파이프라인 확장**: 카드사 소비 매출 데이터, 통신사 생활인구, 분기별 점포 개폐업 이력 데이터 결합 로드맵.
5. **블록체인 분산원장 활용 검토**: 소상공인의 데이터 제공 동의 이력 관리 및 감사 추적 로그 보관 영역에 기술 적용 가능성 검토 (현재 블록체인 미구현임을 명확히 명시).

---

## 4. 금지 표현 및 과장 문구 검증 (Prohibited Claims Audit)

제안서 본문 전체를 전수 검색하여 금지된 표현이 단 1건도 존재하지 않음을 확인하였습니다.

| 금지 / 과장 표현 | 검출 건수 | 제안서 내 순화 및 대체 표현 | 조치 결과 |
| :--- | :---: | :--- | :---: |
| **창업 성공 확률 / 성공 가능성 %** | **0건** | "공공데이터 기반 다차원 상대 입지 적합도 (0~100점)" | **CLEAN** |
| **예상 매출 / 예상 수익 / 매출 예측** | **0건** | "상권 배후수요 및 업종 특화도(LQ) 분석" | **CLEAN** |
| **실제 고객 수 / 실제 방문객 수** | **0건** | "배후 인구수, 타깃 인구 구성비, 대중교통 승하차량" | **CLEAN** |
| **대출 승인 확률 / 대출 가능 금액** | **0건** | "정책자금 지원 요건 안내 및 공공 상담 채널 연계 로드맵" | **CLEAN** |
| **실제 유동인구** | **0건** | "도시철도 및 시내버스 승하차 / 대중교통 이용량" | **CLEAN** |
| **iM뱅크 API 연동 완료 / 제휴 완료** | **0건** | "향후 오픈 API 및 iM뱅크와의 제휴를 통한 연계 가능성 검토" | **CLEAN** |
| **초역세권 / 교육 특구 / 학원가 중심지** | **0건** | "최근접 도시철도역 거리 210m, 학원 점포 수 103개소" | **CLEAN** |
| **딥러닝 / 생성형 AI 예측 모델** | **0건** | "공공데이터 기반 다기준 의사결정형(MCDM) AI 입지 추천 모델" | **CLEAN** |
| **모델 정확도 99%** | **0건** | "Spearman 순위 상관계수 $\rho=0.9894\sim0.9943$" | **CLEAN** |
| **블록체인 기반 서비스 (현재 구현 주장)** | **0건** | "향후 금융 연계 시 데이터 동의 감사 추적 영역에 적용 검토" | **CLEAN** |

---

## 5. 확인 불가 / 제외된 표현 목록 (Rejected Expressions)

다음 표현들은 실제 코드나 공식 검증 데이터에서 근거를 찾을 수 없으므로 제안서 본문에서 전면 제외 및 배제 조치되었습니다.

1. **"대구신용보증재단 연계 비대면 보증대출 심사 보조"**:
   - 사유: Phase 11 Screenshot E 텍스트에 포함되었으나, Phase 10 최종 확정 금융 로드맵 및 실제 협약 사실이 확인되지 않아 삭제 처리함.
2. **"대구형 골목상권 소상공인 데이터 허브 구축"**:
   - 사유: 플랫폼의 거시적 비전일 수 있으나 구체적 실행 주체 및 데이터 파이프라인 검증이 완료되지 않아 제외함.
3. **"초역세권 (범어1동 210m)"**:
   - 사유: 210m는 실제 관측치이나 코드 내 초역세권 판정 임계치 기준이 명시적으로 존재하지 않으므로 객관적 수치("거리 210m")로만 표기함.
4. **"교육 특구 / 대구 최고 학원 밀집지"**:
   - 사유: 외부 상식적 표현이나 Feature Mart 데이터셋 내 공식 변수가 아니므로 "학원 점포 수 103개소, 대구 상위 4.0%"로 대체함.
5. **"인공지능 실시간 매출 추정 알고리즘"**:
   - 사유: 실제 매출 데이터가 부재하며 모델 범위에 포함되지 않으므로 배제함.

---

## 6. 스크린샷 일치성 및 정합성 감사 (Screenshot Consistency Audit)

제안서 본문에서 인용한 모든 시나리오, 점수, 지표가 Phase 11에서 캡처된 실제 4K 스크린샷과 완벽하게 일치함을 확인하였습니다.

| 스크린샷 식별자 | 파일명 | 시나리오 조건 | 본문 인용 수치 | 실제 스크린샷 내 수치 | 일치 여부 |
| :---: | :--- | :--- | :--- | :--- | :---: |
| **Screenshot A** | `01_main_recommendation.png` | 카페 / 2030 / 기본 균형형 | 추천 1위: 신암4동 (77.75점) | 추천 1위: 동구 신암4동 (77.75점) | **100% MATCH** |
| **Screenshot B** | `02_transit_map.png` | 카페 / 2030 / 기본 균형형 | Top 5 카드 및 대구 전역 공간 지도 | 신암4동(77.75), 비산7동(75.83) 등 5개 카드 및 지도 렌더링 | **100% MATCH** |
| **Screenshot C** | `03_explainable_analysis.png` | 학원 / 10대 / 타깃고객 집중형 | 범어1동 84.47점, 103개소, 24.3%, 210m, 18개소, 4,797건 | 6대 지표 카드, 바 차트, 10개 실측치 정량표 100% 일치 | **100% MATCH** |
| **Screenshot D** | `04_model_comparison.png` | 한식 / 전체 / 기본 균형형 | 1위 상인1동 77.47점, $\rho=0.9924$, 90% 일치, $\Delta+3.86$점 | 상단 메트릭 카드 및 순위 비교표 100% 일치 | **100% MATCH** |
| **Screenshot E** | `05_financial_roadmap.png` | Tab 4 금융 로드맵 | **[제안서 삽입 보류 및 제외]** (본문 도식으로 대체) | Phase 10 최종 문구와의 정합성을 위해 이미지 미사용 | **EXCLUDED (SAFE)** |

---

## 7. 500자 요약 분량 정밀 감사

공식 공모전 제안서 양식의 요약문 분량 제한 규정(500자 이내)을 완벽히 충족함을 확인하였습니다.

- **요약문 순수 텍스트**: 470자 (공백 포함)
- **요약문 순수 텍스트 (공백 제외)**: 367자
- **라벨 포함 전체 텍스트**: 483자
- **감사 판정**: **PASS ($\le 500$자 규정 엄격 준수)**

---

## 8. 최종 잔여 리스크 평가 (Remaining Risks)

- **Submission-blocking proposal issue 없음**
- **Feature Freeze 준수**: `app/app.py` 및 모든 모델/데이터 파일의 SHA-256 해시가 변경되지 않았으며, 소스 코드 변경 0건 유지.
- **제출 준비도**: HWPX 양식 이식 시 본 Markdown 문서의 본문, 표, 도식, 스크린샷 가이드를 그대로 반영할 수 있는 완결된 상태 확보.

---

## 9. 최종 감사 판정

# 🟢 PROPOSAL DRAFT READY
