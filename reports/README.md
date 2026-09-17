# 보고서 인덱스

`reports/`는 현재 실행에 필요한 기준 결과와 과거 개발 기록을 분리해 보관합니다.

## 현재 기준

- [`../docs/TEST_REPORT.md`](../docs/TEST_REPORT.md): 전체 103개 테스트 결과
- [`../docs/REPRODUCIBILITY.md`](../docs/REPRODUCIBILITY.md): 실행·검증 재현 절차
- [`../docs/MODEL_CARD.md`](../docs/MODEL_CARD.md): 모델 수식, 범위 및 한계
- [`../docs/DATA_SOURCES.md`](../docs/DATA_SOURCES.md): 데이터 출처와 사용 근거
- [`../submission/phase19_crosslayer_consistency_audit.md`](../submission/phase19_crosslayer_consistency_audit.md): 최종 Cross-Layer 감사
- [`phase7_demo_results.json`](phase7_demo_results.json): 기존 기준선 데모 회귀 테스트가 참조하는 실행 데이터

현재 구현 상태는 위 문서와 `scripts/run_phase*_tests.py`를 우선합니다.

## 보존용 기록

- `archive/development/`: Phase 3~8의 데이터 구축, 모델 실험, UI 및 시각화 기록
- `archive/submission_audits/`: Phase 12~17의 제안서·패키징·호환성 감사 기록

Archive 문서는 작성 당시 상태를 보존한 역사 자료입니다. 일부 경로·명칭·테스트 수·모델 설명은 현재 상태와 다를 수 있으므로 최신 사실의 근거로 사용하지 않습니다.

## 유지관리 원칙

- 현재 기준 문서는 `docs/`에 둡니다.
- 제출 직전 최종 감사와 최종 ZIP만 `submission/`에 둡니다.
- 테스트가 직접 참조하는 결과만 `reports/` 최상위에 둡니다.
- 과거 Phase 기록은 `reports/archive/`에 둡니다.
- `.DS_Store`, `__pycache__`, `*.pyc`, 임시 로그 및 중복 패키징 폴더는 보관하지 않습니다.
