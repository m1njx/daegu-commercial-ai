# 환경 및 결과 재현성 가이드

- 팀: 말괄량이코물이
- 공모전: 2026 AI Blockchain Challenge in Daegu

## 검증 환경

- 실제 실행 검증: macOS Apple Silicon, Python 3.10.21 / 3.11.15 / 3.14.5
- Python 3.12 / 3.13: 이번 호스트에서 미검증
- Streamlit 최소 버전: 1.49.0
- Linux / Windows: 상대경로와 실행 스크립트를 정적으로 점검했으나 이번 호스트에서 직접 실행하지 않음

## 설치와 실행

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
streamlit run app/app.py
```

## 전체 테스트

```bash
python scripts/run_phase6_tests.py
python scripts/run_phase7_validation.py
python scripts/run_phase8_tests.py
python scripts/run_phase9_tests.py
python scripts/run_phase10_tests.py
python scripts/run_phase14c_tests.py
python scripts/run_phase15_hardening_tests.py
python scripts/run_phase16_interactive_regression.py
python scripts/run_phase17_python_compat_tests.py
python scripts/run_phase19_crosslayer_consistency.py
python scripts/run_phase20_data_ui_integrity.py
python scripts/run_phase21_final_defect_closure.py
python scripts/run_phase22_semantic_integrity_tests.py
python scripts/run_phase23_evidence_closure_tests.py
python scripts/run_phase24_zero_trust_tests.py
python scripts/run_phase25_final_document_closure.py
```

기대 결과는 16개 스위트, 총 198/198 PASS입니다.

브라우저 E2E 스크립트 실행 전에는 최초 1회 `python -m playwright install chromium`을 실행합니다. 이는 Playwright의 브라우저 실행 파일 설치 단계이며 일반 앱 실행이나 위 16개 자동화 스위트에는 필요하지 않습니다.

자동화 테스트는 코드 실행, 데이터 무결성, 계산 재현성 및 UI·문서 정합성을 검증합니다. 실제 창업 성과, 매출, 생존율 또는 추천 입지의 사업적 유효성을 검증한 결과는 아닙니다.

## 공식 데모 재현값

모델은 통합 대중교통 모델, `α=0.50`, 점포 미확인 지역 제외 OFF입니다.

| 데모 | 프리셋 | Top 1 | 점수 |
|---|---|---|---:|
| 카페 + 2030 | 기본 균형형 | 신암4동 | 77.75 |
| 한식 + 전체 | 배후 수요 집중형 | 상인1동 | 77.47 |
| 미용실 + 2030 | 기본 균형형 | 칠성동 | 75.45 |
| 학원 + 10대 이하 | 타깃 고객 집중형 | 범어1동 | 84.40 |
| 종합소매 + 전체 | 기본 균형형 | 상인1동 | 72.25 |
| 숙박 + 2030 | 기본 균형형 | 칠성동 | 75.90 |

## 결정론적 정렬

`ranking.py`는 `[total_score, demand_score, target_fit_score, pop_total]`을 모두 내림차순으로 정렬합니다. 최종 데이터에서 이 복합 정렬키는 행별 고유합니다.

## 모델 비교 수치의 의미

6개 데모에서 도시철도 중심 개선 모델과 통합 대중교통 모델의 전체 행정동 Spearman 범위는 $\rho=0.9915\sim0.9969$입니다. 이는 두 모델의 순위가 유사하다는 의미이며 추천 입지의 사업적 정확도 또는 창업 성공 가능성을 의미하지 않습니다.

## 제출 파일 구조

코드 ZIP과 `submission/documents/제안 요약서.pdf`는 별도 제출 파일입니다. 코드 ZIP은 PDF를 포함하지 않으며, ZIP 내부 `CHECKSUMS.sha256`으로 코드 패키지 파일을 검증합니다.
