# Phase 17 Python Compatibility Report

## 1. Executive Summary

Phase 9 테스트의 Python 3.10/3.11 비호환 f-string 네 곳을 최소 수정했다. Production 앱·추천 모델·데이터·수식은 변경하지 않았다. Python 3.11.15와 3.14.5에서 전체 89/89 테스트가 통과했다. Python 3.10은 설치되어 있지 않아 실제 실행 결과를 주장하지 않으며, 3.10 대상 문법 제약과 dependency resolver만 확인했다.

## 2. Reproduced SyntaxError

Before:

- Python: 3.11.15 (Python 3.10과 동일한 해당 f-string 문법 제한)
- Command: `python3.11 scripts/run_phase9_tests.py`
- Result: `SyntaxError: f-string: unmatched '['` at line 141
- `compileall`에서 line 141 수정 후 동일 문제가 line 160에서도 추가 검출됨

After:

- Python 3.11.15: Phase 9 10/10 PASS
- Python 3.14.5: Phase 9 10/10 PASS
- Python 3.10: interpreter 미설치로 runtime `NOT TESTED`

## 3. Root Cause

Python 3.12의 PEP 701은 f-string 표현식 파싱 제약을 완화했다. 기존 테스트는 큰따옴표 f-string 내부에서 `top1["adm_nm"]`처럼 같은 큰따옴표를 재사용하여 Python 3.10/3.11 파서에서 문자열이 조기에 종료됐다. 내부 key 인용부호만 작은따옴표로 변경했다.

## 4. Files Fixed

- `scripts/run_phase9_tests.py`: f-string 내부 DataFrame key 인용부호 네 곳
- `scripts/run_phase17_python_compat_tests.py`: 신규 7개 호환성 회귀 테스트
- 제출 package의 README, README_JUDGE, REPRODUCIBILITY, TEST_REPORT, PROJECT_STRUCTURE, MODEL_CARD, manifest, checksums
- 루트 README의 검증 환경 문구

## 5. Full Python Syntax Audit

| File | Line | 이전 문법 | Python 3.10 | Python 3.11 | Python 3.12+ | Fix |
|---|---:|---|---|---|---|---|
| `scripts/run_phase9_tests.py` | 141 | `f"...{top1["adm_nm"]}..."` | SyntaxError | SyntaxError | Parse | 내부 quote 변경 |
| 동일 | 142 | `f"...{top1["total_score"]}..."` | SyntaxError | SyntaxError | Parse | 내부 quote 변경 |
| 동일 | 160 | `f"...{top1["adm_nm"]}..."` | SyntaxError | SyntaxError | Parse | 내부 quote 변경 |
| 동일 | 161 | `f"...{top1["total_score"]}..."` | SyntaxError | SyntaxError | Parse | 내부 quote 변경 |

수정 후 `app/`, `src/`, `scripts/`의 Python 파일 38개가 Python 3.11 및 3.14 compileall을 통과했다. `typing.Self`, `tomllib`, `ExceptionGroup`, `except*` 등 Python 3.11+ 전용 API 사용은 발견되지 않았다.

## 6. Interpreter Matrix

| Version | Installed | Compileall | Phase 9 | Full Suite | Status |
|---|---|---|---|---|---|
| Python 3.10 | No | NOT TESTED | NOT TESTED | NOT TESTED | 문법 제약 정적 검토 및 dependency resolver PASS |
| Python 3.11.15 | Yes | PASS | 10/10 | 89/89 | PASS |
| Python 3.12 | No | NOT TESTED | NOT TESTED | NOT TESTED | 미검증 |
| Python 3.13 | No | NOT TESTED | NOT TESTED | NOT TESTED | 미검증 |
| Python 3.14.5 | Yes | PASS | 10/10 | 89/89 | PASS |

Python 3.10 대상으로 `pip --dry-run --python-version 3.10 --only-binary=:all:`을 실행했으며 requirements 전체가 호환 wheel 조합으로 해석됐다. 이는 실제 Python 3.10 실행을 대체하지 않는다.

## 7. Documentation Claims Before/After

| Before | After |
|---|---|
| Python 3.10~3.14 호환 확인 완료 | 전체 실행 검증: Python 3.11.15, 3.14.5 |
| 여러 OS 직접 검증으로 오해 가능한 표현 | 실제 검증 OS와 정적 점검 OS 분리 |
| 총 82/82 | 기존 82 + Phase 17 7 = 89/89 |

## 8. REPRODUCIBILITY.md Audit

설치되지 않은 Python 3.10/3.12/3.13을 `NOT TESTED`로 명시하고 실제 검증 환경만 기록했다. Phase 17 명령과 89/89 기대 합계를 추가했다.

## 9. README_JUDGE Audit

Phase 6~17의 아홉 실행 명령이 모두 존재하며, Phase 16 및 Phase 17 기대 결과와 총 89/89가 명시되어 있다. Clean Room에서 같은 순서로 실행했다.

## 10. Full Regression

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
| Total | 89/89 |

위 결과는 Python 3.11.15와 Python 3.14.5에서 각각 확인했다.

## 11. Phase17 Tests

7/7 PASS: Phase 9 AST, 전체 compile, 알려진 비호환 패턴, 문서 호환 주장, Phase 9 실제 subprocess, README_JUDGE 명령, manifest·문서 테스트 합계를 검사한다.

## 12. Production Hash Preservation

| File | Phase 16 / Before | Phase 17 / After | Status |
|---|---|---|---|
| `app/app.py` | `d70a4be486d7336bd3a170e0a68902daa813783bcb1bc46076512d2da32644ea` | 동일 | Unchanged |
| `scoring.py` | `e620cd83cc769f4f1f0e575d076221ffc77eb4f9bd1320b06fbab9bfb4b76d6e` | 동일 | Unchanged |
| `improved.py` | `c4723a71e0f4e1c0ce9cedcc82e7de1f193f54fa3b05f44e7eac55864a017b75` | 동일 | Unchanged |
| `transit_enhanced.py` | `c16f3a86217bb5b6e30cc7bdaed5f30f0816b32a4c6bc83449bcc38eee981471` | 동일 | Unchanged |
| `explain.py` | `1e7e5d6f35ba42ec944b33a0bd8f31e6a648d3ce6a1bc9e5ed575af2f0d9bca1` | 동일 | Unchanged |
| `ranking.py` | `a75c3079b6b4a746714bcc391c3452fbd656c1d56251b71439d4053898f8615b` | 동일 | Unchanged |
| `personalization.py` | `fc02c48a8d4ea071d42204f8e708abf16979e3e825e28fc1e4fbe09c9e0d0ce2` | 동일 | Unchanged |
| `feature_builder.py` | `edab8ca489b19310b7deb91d6d76a7387a776226175fc45bb582accc4e93fc30` | 동일 | Unchanged |

## 13. Clean Room

- Path: `/tmp/daegu_phase17_clean.WqAXkm`
- ZIP extraction: PASS
- CHECKSUMS: 58/58 PASS
- Python 3.11 compileall: PASS
- Phase 9: 10/10 PASS
- Full suite: 89/89 PASS
- Streamlit Python 3.11 startup and HTTP health: PASS (temporary port 8519)

## 14. Final ZIP

- Filename: `말괄량이코물이_대구소상공인_AI_입지추천_제출코드_FINAL_COMPAT.zip`
- Size: 16,490,172 bytes
- SHA-256: `d02ab63bbeb5c4ee01e2ccfcde4db0239cd4708ce9e93cca273c433443ed5ac2`

## 15. Remaining Risks

Python 3.10 interpreter가 감사 호스트에 없어 Phase 9 10/10과 전체 스위트를 해당 버전에서 직접 실행하지 못했다. 코드가 Python 3.11 파서에서 compile되고 3.10용 dependency resolution이 성공했으나, 엄격한 의미의 Python 3.10 runtime 검증은 남아 있다. Python 3.12/3.13 및 Linux/Windows도 이번 호스트에서 직접 실행하지 않았다.

## 16. Final Verdict

**🟡 VERIFIED ONLY ON LIMITED PYTHON VERSIONS**

Python 호환성 결함은 수정됐고 검증되지 않은 호환 완료 주장은 제거했다. 다만 요청된 최종 acceptance criterion에 Python 3.10 실제 실행이 포함되어 있으므로, 해당 인터프리터 없이 녹색 판정을 내리지 않는다.
