#!/usr/bin/env python3
"""Phase 17: Python syntax compatibility and reproducibility regression tests."""

from __future__ import annotations

import ast
import json
import py_compile
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
SOURCE_DIRS = (ROOT_DIR / "app", ROOT_DIR / "src", ROOT_DIR / "scripts")
SUITE_COUNTS = {
    "phase6": 10,
    "phase7": 12,
    "phase8": 10,
    "phase9": 10,
    "phase10": 10,
    "phase14c": 6,
    "phase15": 12,
    "phase16": 12,
    "phase17": 7,
    "phase19": 14,
    "phase20": 14,
    "phase21": 15,
    "phase22": 18,
    "phase23": 14,
    "phase24": 20,
    "phase25": 14,
}
EXPECTED_TOTAL = sum(SUITE_COUNTS.values())


def metadata_root() -> Path:
    if (ROOT_DIR / "submission_manifest.json").is_file():
        return ROOT_DIR
    package_dir = ROOT_DIR / "submission" / "package"
    candidates = sorted(package_dir.glob("*/submission_manifest.json"))
    assert len(candidates) == 1, "submission_manifest.json 위치를 하나로 확정할 수 없습니다."
    return candidates[0].parent


def python_files() -> list[Path]:
    return sorted(path for directory in SOURCE_DIRS for path in directory.rglob("*.py"))


def main() -> None:
    print("=" * 70)
    print("PHASE 17: Python 호환성 및 재현성 7대 회귀 테스트")
    print("=" * 70)

    phase9 = ROOT_DIR / "scripts" / "run_phase9_tests.py"
    ast.parse(phase9.read_text(encoding="utf-8"), filename=str(phase9))
    print("[PASS] Test 1: run_phase9_tests.py AST parse")

    files = python_files()
    for path in files:
        py_compile.compile(str(path), doraise=True)
    print(f"[PASS] Test 2: app/src/scripts Python 파일 {len(files)}개 compile")

    source = phase9.read_text(encoding="utf-8")
    assert 'top1["adm_nm"]} !=' not in source
    assert 'top1["total_score"]} !=' not in source
    print("[PASS] Test 3: 알려진 Python 3.10/3.11 비호환 f-string 패턴 0건")

    meta_root = metadata_root()
    reproducibility = (meta_root / "docs" / "REPRODUCIBILITY.md").read_text(encoding="utf-8")
    prohibited_claims = ("3.10 ~ 3.14 호환 확인 완료", "3.10.x, 3.11.x, 3.12.x, 3.14.x 전 계열 호환 확인 완료")
    assert not any(claim in reproducibility for claim in prohibited_claims)
    print("[PASS] Test 4: 검증되지 않은 Python 전 버전 호환 완료 주장 0건")

    result = subprocess.run(
        [sys.executable, str(phase9)], cwd=ROOT_DIR, text=True, capture_output=True, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ALL 10 PHASE 9 AUTOMATED TESTS PASSED" in result.stdout
    print(f"[PASS] Test 5: Phase 9 실제 실행 10/10 ({sys.version.split()[0]})")

    judge = (meta_root / "README_JUDGE.md").read_text(encoding="utf-8")
    for script in (
        "run_phase9_tests.py",
        "run_phase16_interactive_regression.py",
        "run_phase17_python_compat_tests.py",
    ):
        assert f"python scripts/{script}" in judge
    print("[PASS] Test 6: README_JUDGE 전체 테스트 실행 명령")

    manifest = json.loads((meta_root / "submission_manifest.json").read_text(encoding="utf-8"))
    suites = manifest["tests"]["suites"]
    actual = sum(item["tests"] for item in suites.values())
    passed = sum(item["passed"] for item in suites.values())
    assert {name: suites[name]["tests"] for name in SUITE_COUNTS} == SUITE_COUNTS
    assert actual == passed == manifest["tests"]["total"] == manifest["tests"]["passed"] == EXPECTED_TOTAL
    for relative in ("README.md", "README_JUDGE.md", "docs/TEST_REPORT.md", "docs/REPRODUCIBILITY.md"):
        document = "".join((meta_root / relative).read_text(encoding="utf-8").split())
        assert f"{EXPECTED_TOTAL}/{EXPECTED_TOTAL}" in document
    print(f"[PASS] Test 7: manifest suite 합계와 심사 문서 {EXPECTED_TOTAL}/{EXPECTED_TOTAL} 일치")

    print("=" * 70)
    print("PHASE 17: 7/7 PASS")
    print("=" * 70)


if __name__ == "__main__":
    main()
