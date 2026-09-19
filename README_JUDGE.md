# 심사위원 실행·검증 가이드

- 팀명: 말괄량이코물이
- 공모전: 2026 AI Blockchain Challenge in Daegu
- 프로젝트: 대구 소상공인 AI 상권·창업 입지 추천 서비스

## 1. 실행

검증된 Python은 3.10.21, 3.11.15, 3.14.5입니다.

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
streamlit run app/app.py
```

브라우저에서 `http://localhost:8501`을 엽니다. 별도 API 키나 외부 서비스 연결은 필요하지 않습니다.

## 2. UI 검증 순서

1. 데모 `카페 + 2030`을 선택합니다.
   - 통합 대중교통 모델, 기본 균형형, `α=0.50`
   - Top 1: 신암4동, 77.75점
2. 데모 `학원 + 10대 이하 (0~19세)`를 선택합니다.
   - Top 1: 범어1동, 84.40점
3. 데모 `숙박 + 2030`을 선택합니다.
   - Top 1: 칠성동, 75.90점
4. 고급 설정에서 `α`를 0.30 / 0.50 / 0.80으로 바꿉니다.
   - 모델 설명과 비교 표 제목에 현재 값이 표시됩니다.
5. 모델 비교 탭을 엽니다.
   - 동일한 `α`에서 도시철도 중심 개선 모델과 통합 대중교통 모델을 비교합니다.
   - 할인 적용 전후 비교가 아닙니다.
6. 데이터/원본 탭에서 CSV를 내려받습니다.
   - UTF-8-SIG(BOM)로 저장됩니다.

UI에는 `기본 균형형`, `타깃 고객 집중형 (트렌디/특화 소비)`을 포함한 6개 가중치 프리셋과 `⚖️ 통합 대중교통 모델 vs 도시철도 중심 개선 모델` 비교 탭이 있습니다.

## 3. 모델 의미

본 모델은 공공데이터 기반 MCDM 상대적 입지 적합도 모델입니다. 6개 컴포넌트 기본 가중치는 배후수요 30%, 타깃적합 20%, 경쟁 15%, 대중교통 15%, 주차 10%, 업종특화 10%입니다.

- 경쟁점포: 사용자가 선택한 업종 집합 전체의 반경 300m 경쟁점포
- Industry Fit: LQ 백분위 100%
- 접근성: 도시철도 70% + 시내버스 30%
- 점포 미확인 지역: 현재 `α`로 경쟁점수 보정

6개 공식 데모의 도시철도 중심 모델과 통합 대중교통 모델 간 Spearman 범위는 $\rho=0.9915\sim0.9969$입니다. 이는 두 모델의 전체 행정동 순위가 유사하다는 의미입니다. 추천 입지의 사업적 정확도 또는 창업 성공 가능성을 의미하지 않습니다.

## 4. 전체 자동화 테스트

```bash
python scripts/run_phase6_tests.py                 # 10
python scripts/run_phase7_validation.py            # 12
python scripts/run_phase8_tests.py                 # 10
python scripts/run_phase9_tests.py                 # 10
python scripts/run_phase10_tests.py                # 10
python scripts/run_phase14c_tests.py               # 6
python scripts/run_phase15_hardening_tests.py      # 12
python scripts/run_phase16_interactive_regression.py # 12
python scripts/run_phase17_python_compat_tests.py  # 7
python scripts/run_phase19_crosslayer_consistency.py # 14
python scripts/run_phase20_data_ui_integrity.py    # 14
python scripts/run_phase21_final_defect_closure.py # 15
python scripts/run_phase22_semantic_integrity_tests.py # 18
python scripts/run_phase23_evidence_closure_tests.py # 14
python scripts/run_phase24_zero_trust_tests.py     # 20
python scripts/run_phase25_final_document_closure.py # 14
python scripts/run_final_defect_closure_tests.py   # 15
```

기대 합계: 213/213 PASS (17개 스위트).

브라우저 E2E 검증 스크립트를 직접 실행하려면 최초 1회 `python -m playwright install chromium`으로 Chromium 실행 파일을 설치합니다. 앱 실행과 위 17개 자동화 스위트에는 별도의 브라우저 다운로드가 필요하지 않습니다.

자동화 테스트는 코드 실행, 데이터 무결성, 계산 재현성 및 UI·문서 정합성을 검증합니다. 실제 창업 성과, 매출, 생존율 또는 추천 입지의 사업적 유효성을 검증한 결과는 아닙니다.

## 5. 한계

- 실제 매출 및 창업 성공·폐업 ground truth 없음
- 임대료·권리금·실시간 공실률 미포함
- 행정동 단위 비교이므로 필지별 현장 확인 필요
- 금융 로드맵 2~4단계는 향후 확장이고 현재 구현은 AI 입지 추천 중심

코드 ZIP과 제안 요약서 PDF는 별도 제출 파일입니다.
