# 보고서 인덱스

이 디렉터리는 프로젝트의 단계별 분석 근거와 재현 결과를 보관한다. 과거 단계의 보고서는 당시 상태를 기록한 문서이므로, 현재 구현 상태를 판단할 때는 아래의 **현재 기준 문서**와 자동 테스트를 우선한다.

## 현재 기준

1. [`phase8_comprehensive_bus_and_data_strategy_report.md`](phase8_comprehensive_bus_and_data_strategy_report.md) — 도시철도·버스 통합 데이터 전략과 Phase 8 종합 결과
2. [`phase8_bus_integration_report.md`](phase8_bus_integration_report.md) — 버스 데이터 결합 방식과 검증 상세
3. [`../submission/phase12_proposal_audit.md`](../submission/phase12_proposal_audit.md) — 제안서 수치·문구 근거 감사
4. [`../submission/phase13_hwpx_final_report.md`](../submission/phase13_hwpx_final_report.md) — 최종 HWPX 조립 및 제출 준비 상태
5. `scripts/run_phase9_tests.py`, `scripts/run_phase10_tests.py` — 현재 서비스 통합 및 UI 릴리스 기준 자동 검증

## 단계별 역사 기록

| 단계 | 문서 | 역할 | 현재 해석 |
|---|---|---|---|
| Phase 3 | [`phase3_commercial_data_report.md`](phase3_commercial_data_report.md) | 상가 API 수집·품질 검증 | 원천 수집 근거 |
| Phase 4 | [`phase4_feature_mart_report.md`](phase4_feature_mart_report.md) | 공간 결합·Feature Mart | 데이터 구축 근거 |
| Phase 5 | [`phase5_recommendation_report.md`](phase5_recommendation_report.md) | 최초 추천 모델 | 초기 기준선 기록 |
| Phase 5 | [`phase5_code_audit_report.md`](phase5_code_audit_report.md) | 추천 코드 감사 | 초기 기준선 감사 |
| Phase 6 | [`phase6_prototype_report.md`](phase6_prototype_report.md) | Improved 모델·프로토타입 | 후속 Phase 7~10에서 개선됨 |
| Phase 6 | [`phase6_code_audit_report.md`](phase6_code_audit_report.md) | 당시 조건부 감사 | 당시 지적사항은 후속 단계에서 해소됨 |
| Phase 7 | [`phase7_validation_report.md`](phase7_validation_report.md) | 통합 검증 | 도시철도 중심 버전 기록 |
| Phase 7 | [`phase7_ui_final_redesign_report.md`](phase7_ui_final_redesign_report.md) | UI 개편 | Phase 10 이전 UI 기록 |
| Phase 7 | [`phase7_score_status_color_report.md`](phase7_score_status_color_report.md) | 점수 색상 기준 | 현재도 유효 |
| Phase 7 | [`phase7_proposal_data.md`](phase7_proposal_data.md) | 제안서 데이터집 | Phase 12 감사본 우선 |
| Phase 8 | [`phase8_bus_integration_report.md`](phase8_bus_integration_report.md) | 버스 통합 | 현재 모델 근거 |
| Phase 8 | [`phase8_comprehensive_bus_and_data_strategy_report.md`](phase8_comprehensive_bus_and_data_strategy_report.md) | 종합 전략 | 현재 데이터 기준 |

## 기계 판독 산출물

- `phase3_validation_result.json`: 상가 데이터 품질 결과
- `phase5_example_results.json`: 초기 모델 예시 결과
- `phase6_baseline_vs_improved.json`: 기준선·개선 모델 비교
- `phase7_demo_results.json`: 도시철도 중심 데모 기준값
- `phase8_experiment_results.json`: 버스 통합 실험 결과

이 JSON 파일은 보고서의 근거 데이터이므로 임의 편집하지 않고 생성 스크립트로 갱신한다.

## 시각화

`figures/`는 Phase 4~5 분석에서 생성한 PNG 및 Folium HTML 산출물이다. 현재 대시보드 UI 캡처는 `submission/screenshots/`에 있다.

## 유지관리 원칙

- 새 최종 보고서를 추가하면 이 인덱스의 현재 기준을 갱신한다.
- 과거 보고서는 삭제하거나 최신 사실처럼 덮어쓰지 않고 역사 기록으로 보존한다.
- `.DS_Store`, `__pycache__`, `*.pyc`, 임시 로그는 보고서 산출물로 취급하지 않는다.
- 팀 전달용 동결본은 `team_handoff_20260908/`과 루트 ZIP에 보관하며 현재 소스와 혼용하지 않는다.
