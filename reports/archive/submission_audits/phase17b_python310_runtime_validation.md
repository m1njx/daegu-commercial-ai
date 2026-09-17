# Phase 17B Python 3.10 Runtime Validation

## 1. Executive Verdict

Python 3.10.21을 Homebrew 병렬 formula로 설치하고, 기존 시스템 기본 Python을 변경하지 않은 채 `FINAL_COMPAT.zip`을 새 Clean Room에 해제하여 독립 검증했다. requirements 설치, pip 무결성, compileall, Phase 9 10/10, 전체 89/89, Streamlit 및 실제 Chromium smoke가 모두 통과했다.

## 2. Host Environment

- OS: macOS 26.6.2 (Build 25G83)
- Architecture: Apple Silicon `arm64`
- 기존 기본 `python3`: Python 3.14.5
- 기존 별도 interpreter: Python 3.11.15
- Phase 17B 설치: Python 3.10.21

## 3. Python 3.10 Installation

- Method: Homebrew `python@3.10` bottle
- Command: `brew install python@3.10`
- Exact version: Python 3.10.21
- Binary: `/opt/homebrew/bin/python3.10`
- Result: PASS
- 시스템 기본 Python 변경: 없음 (`python3 --version`은 계속 3.14.5)
- `pyenv global`, 시스템 Python 삭제/덮어쓰기, `sudo` 사용: 없음

## 4. Clean Room

- 최초 검증 경로: `/tmp/daegu_phase17b_py310.f3vFHY`
- 검증 ZIP: `말괄량이코물이_대구소상공인_AI_입지추천_제출코드_FINAL_COMPAT.zip`
- 전용 venv: Clean Room 내부 `.venv310`
- 최종 VERIFIED ZIP 재검증 경로: `/tmp/daegu_phase17b_verified.UDCvvE`
- 원본 프로젝트 source/data 참조: 0

## 5. Dependency Installation

- `python -m pip install --upgrade pip`: PASS
- `python -m pip install -r requirements.txt`: PASS
- resolver conflict/build failure/unsupported Python warning: 0
- `python -m pip check`: `No broken requirements found.`
- pandas, numpy, geopandas, shapely, pyproj, scipy, matplotlib, pyarrow, requests, chardet, folium, streamlit: 12/12 import PASS

## 6. compileall

Python 3.10.21에서 `python -m compileall -q app src scripts`: PASS. SyntaxError 및 compile failure 0건이다.

## 7. Phase 9

`python scripts/run_phase9_tests.py`: **10/10 PASS**.

- SyntaxError: 0
- ImportError: 0
- KeyError: 0
- assertion failure: 0

## 8. Full Test Suite

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
| Total | **89/89 PASS** |

최초 `FINAL_COMPAT.zip` Clean Room과 문서 갱신 후 `FINAL_COMPAT_VERIFIED.zip` 재해제 환경에서 각각 통과했다.

## 9. Streamlit

- Interpreter: Python 3.10.21 venv
- Port: 8520 (검증 후 종료)
- Startup: PASS
- Health endpoint: `ok`
- Root HTTP: 200
- Runtime traceback/import error/data load failure: 0

## 10. Browser Smoke

Chromium headless에서 다음을 실제 조작했다.

- Demo 1, 2, 4, 6
- 숙박 + Baseline + 미진입 상권 제외 ON
- 5개 탭
- 지도 iframe
- CSV 다운로드
- console error, Streamlit exception, 사용자 노출 warning: 0

기존 Phase 16 브라우저 스크립트는 최신 Streamlit 1.63 DOM에서 `button[role=tab]` selector와 탭 상태 가정 때문에 후반 타임아웃이 발생했다. 서버 오류는 없었으며, 제출 코드를 수정하지 않고 `/tmp` 검증 스크립트에서 `[role=tab]` 및 실제 CSV 탭을 명시하여 기능을 독립 확인했다.

## 11. Representative Results

| Model / Scenario | Python 3.10 Result |
|---|---|
| Integrated 카페 + 2030 기본 | 신암4동 77.75 |
| Integrated 학원 + 10대 타깃 집중 | 범어1동 84.47 |
| Integrated 숙박 + 2030 | 감삼동 75.82 |
| Baseline 카페 + 2030 | 신암4동 77.93 |
| Baseline 한식 + 전체 | 진천동 71.54 |
| Baseline 숙박 + 2030 | 감삼동 77.00 |

Integrated 결과는 브라우저/Phase 16에서, Baseline 결과는 Phase 9 회귀에서 확인했다.

## 12. Cross-Version Comparison

Python 3.10.21, 3.11.15, 3.14.5 모두 전체 89/89를 통과했다. 대표 Top1·점수·순위에 실질적 차이가 없었고, Phase 8/9의 Spearman 및 Phase 10 CSV 회귀도 동일하게 통과했다.

## 13. README_JUDGE Reproduction

ZIP 해제 → 프로젝트 이동 → Python 3.10 venv 생성 → requirements 설치 → 테스트 → Streamlit 순서로 숨은 source/data 단계 없이 재현했다. README_JUDGE의 Python 실행 명령과 실제 파일 경로가 일치했다.

## 14. Production Code Changes

0건. 다음 핵심 파일의 SHA-256은 Phase 17 시작 전과 동일하다.

- `app/app.py`: `d70a4be486d7336bd3a170e0a68902daa813783bcb1bc46076512d2da32644ea`
- `scoring.py`: `e620cd83cc769f4f1f0e575d076221ffc77eb4f9bd1320b06fbab9bfb4b76d6e`
- `improved.py`: `c4723a71e0f4e1c0ce9cedcc82e7de1f193f54fa3b05f44e7eac55864a017b75`
- `transit_enhanced.py`: `c16f3a86217bb5b6e30cc7bdaed5f30f0816b32a4c6bc83449bcc38eee981471`
- `explain.py`: `1e7e5d6f35ba42ec944b33a0bd8f31e6a648d3ce6a1bc9e5ed575af2f0d9bca1`
- `ranking.py`: `a75c3079b6b4a746714bcc391c3452fbd656c1d56251b71439d4053898f8615b`
- `personalization.py`: `fc02c48a8d4ea071d42204f8e708abf16979e3e825e28fc1e4fbe09c9e0d0ce2`
- `feature_builder.py`: `edab8ca489b19310b7deb91d6d76a7387a776226175fc45bb582accc4e93fc30`

## 15. Documentation Changes

README, README_JUDGE, REPRODUCIBILITY, TEST_REPORT 및 manifest의 Python 3.10 상태를 `runtime verified`로 갱신했다. Python 3.12/3.13은 계속 미검증으로 명시했다. 테스트 총수는 변경 없이 89개다.

## 16. Final ZIP

- Filename: `말괄량이코물이_대구소상공인_AI_입지추천_제출코드_FINAL_COMPAT_VERIFIED.zip`
- Size: 16,490,259 bytes
- SHA-256: `5ffe6d465edf7e662989d290836ae8b8cd9420e6a128a21c69e69dc166550fb7`
- CHECKSUMS: 58/58 PASS
- ZIP integrity: PASS
- `.venv310`, pyenv/brew 파일, installer, cache, `__pycache__`, `.pyc`: 0

기존 `FINAL_COMPAT.zip`은 보존했다.

## 17. Remaining Risks

Python 3.12/3.13 및 Linux/Windows는 이번 호스트에서 직접 실행하지 않았다. Python 3.10·3.11·3.14 macOS 검증 범위에서는 제출 차단 문제가 없다. Streamlit 1.63은 bare-mode 테스트 시 `st.components.v1.html` deprecation 안내를 터미널에 출력하지만 사용자 화면 오류가 아니며 이번 검증 범위의 Production 변경 사유로 보지 않았다.

## 18. Final Verdict

**🟢 PYTHON 3.10 RUNTIME VERIFIED / FINAL READY**
