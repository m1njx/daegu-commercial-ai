# Daegu Commercial AI

대구광역시 150개 행정동의 공공데이터를 결합해 소상공인 창업 입지 적합도를 비교하는 Streamlit 대시보드입니다. 업종, 목표 고객층, 사용자 가중치를 입력하면 수요·타깃 적합도·경쟁 기회도·대중교통 접근성·주차 공급·업종 특화도를 0~100점의 상대 점수로 계산하고 추천 순위를 제공합니다.

> 이 서비스는 창업 성공률이나 예상 매출을 예측하지 않습니다. 결과는 대구시 행정동 간 상대적 입지 적합도이며, 실제 계약 전 현장 조사와 인허가 검토가 필요합니다.

## 주요 기능

- 대구 150개 행정동과 118,357개 점포 분석
- 도시철도 94개 역과 시내버스 3,981개 정류소 접근성 결합
- 업종·연령대별 동적 Feature Mart 생성
- 6개 평가 컴포넌트와 사용자 가중치 정규화
- 초기 기준선, 도시철도 중심 개선, 통합 대중교통 모델 비교
- 점포 0개 지역의 무경쟁 착시 보정 및 완전 제외 옵션
- Top 5 추천 카드, 행정동 지도, 상세 분석, CSV 다운로드
- 데이터 기반 추천 설명과 모델 민감도 검증

## 모델 구조

```text
공공 원천 데이터
  → 공간 결합 및 품질 검증
  → 행정동·점포 Feature Mart
  → 6대 컴포넌트 백분위 점수
  → 개인화 가중합
  → Baseline / Improved / Transit-integrated 랭킹
  → 설명·지도·다운로드
```

기본 가중치는 수요 30%, 타깃 적합도 20%, 경쟁 기회도 15%, 교통 접근성 15%, 주차 공급 10%, 업종 특화도 10%입니다. 통합 대중교통 모델은 교통 접근성 컴포넌트 내부에서 도시철도 70%와 시내버스 30%를 사용합니다.

## 빠른 실행

Python 3.10 이상을 권장합니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app/app.py --server.headless true --server.port 8502
```

브라우저에서 `http://localhost:8502`로 접속합니다. 대시보드 실행에 필요한 가공 데이터는 `data/processed/`에 포함되어 있어 별도의 API 키가 필요하지 않습니다.

## 검증

```bash
python3 scripts/run_phase6_tests.py
python3 scripts/run_phase7_validation.py
python3 scripts/run_phase9_tests.py
python3 scripts/run_phase10_tests.py
```

검증 범위에는 150개 행정동 완전성, 점수 범위, NaN/Inf, 순위 연속성, 극단 가중치, 0점포 보정, 버스 피처 결합, 데모 시나리오 재현성과 Streamlit UI 무결성이 포함됩니다.

`scripts/run_phase8_tests.py`는 저장소에서 제외된 시내버스 원천파일까지 검사하는 재구축 검증입니다. `data/raw/bus/`에 보고서에 명시된 원천파일을 배치한 경우에만 별도로 실행합니다.

## 디렉터리

```text
app/                    Streamlit 애플리케이션과 이미지 에셋
data/processed/         실행 및 검증에 필요한 가공 데이터
src/features/           버스 공간 피처 생성
src/recommendation/     피처·점수·랭킹·개인화·설명 모듈
scripts/                수집, 생성, 검증, 회귀 테스트
reports/                단계별 분석 보고서와 시각화
submission/             제안서 근거 감사 및 조립 기록
```

보고서의 현재 기준과 역사 문서는 [`reports/README.md`](reports/README.md)에서 구분해 확인할 수 있습니다.

## 원천데이터와 보안

대용량 원천데이터는 저장소에 포함하지 않습니다. 원천데이터를 다시 수집하거나 Feature Mart를 재생성하려면 각 스크립트의 데이터 출처와 예상 경로를 확인하세요.

공공데이터포털 API를 사용하는 경우 키는 코드나 설정 파일에 저장하지 않고 환경변수로만 전달합니다.

```bash
export DATA_GO_KR_API_KEY="your-api-key"
python3 scripts/collect_commercial_data.py
```

`.env`, API 키, 로컬 캐시, 원천데이터, 팀 전달 ZIP 및 생성된 제출 바이너리는 `.gitignore`로 제외됩니다.

## 데이터 해석 시 주의사항

- 점수는 대구시 내부의 백분위 기반 상대 점수입니다.
- 교통 지표는 도시철도와 버스의 승하차 관측치를 사용하며 통신사 실시간 유동인구가 아닙니다.
- 주차 지표는 건축물대장 기반 부설주차 수용능력 proxy입니다.
- 점포 0개 지역은 기회와 시장 미형성 위험을 동시에 가지므로 현장 확인이 필수입니다.
- 데이터 기준일과 세부 출처는 `reports/`의 단계별 보고서를 따릅니다.
