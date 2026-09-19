#!/usr/bin/env python3
"""Build the deterministic Phase 22 judge code package and checksums."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
import hashlib
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "말괄량이코물이_대구소상공인_AI_입지추천"
ZIP_PATH = ROOT / "submission/말괄량이코물이_대구소상공인_AI_입지추천_제출코드_FINAL_SUBMISSION.zip"

ROOT_FILES = (".env.example", "LICENSE", "LICENSES.md", "README.md", "README_JUDGE.md", "requirements.txt", "submission_manifest.json")
TREES = (".streamlit", "app", "src", "scripts", "docs", "data")
REPORTS = (
    "reports/phase7_demo_results.json",
    "reports/phase22_impact_analysis.md",
    "reports/phase24_impact_analysis.json",
    "reports/final_defect_closure_matrix.md",
    "reports/final_defect_closure_report.md",
    "reports/store_boundary_mismatches.csv",
)
SCREENSHOT_NAMES = (
    "01_main_recommendation.png", "02_transit_map.png", "03_explainable_analysis.png",
    "04_model_comparison.png", "05_financial_roadmap.png"
)
EXCLUDE_PARTS = {"__pycache__", ".git", ".venv", ".DS_Store"}


def allowed(path: Path) -> bool:
    return not any(part in EXCLUDE_PARTS for part in path.parts) and path.suffix != ".pyc" and not path.name.endswith(".egg-info")


def copy_file(rel: str, stage: Path) -> None:
    src = ROOT / rel
    if not src.is_file():
        return
    dst = stage / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="daegu_pkg_") as temp_dir:
        stage_parent = Path(temp_dir)
        stage = stage_parent / PACKAGE_NAME
        stage.mkdir(parents=True)

        for rel in ROOT_FILES + REPORTS:
            copy_file(rel, stage)

        # Canonical screenshot packaging
        shots_dir = ROOT / "screenshots" if (ROOT / "screenshots").is_dir() else ROOT / "submission/screenshots"
        for s_name in SCREENSHOT_NAMES:
            s_src = shots_dir / s_name
            if s_src.is_file():
                s_dst = stage / "screenshots" / s_name
                s_dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(s_src, s_dst)

        for tree in TREES:
            for src in sorted((ROOT / tree).rglob("*")):
                if src.is_file() and allowed(src.relative_to(ROOT)):
                    copy_file(src.relative_to(ROOT).as_posix(), stage)

        files = sorted(p for p in stage.rglob("*") if p.is_file())
        lines = [f"{digest(path)}  {path.relative_to(stage).as_posix()}" for path in files]
        checksum = stage / "CHECKSUMS.sha256"
        checksum.write_text("\n".join(lines) + "\n", encoding="utf-8")
        shutil.copy2(checksum, ROOT / "CHECKSUMS.sha256")

        ZIP_PATH.parent.mkdir(parents=True, exist_ok=True)
        if ZIP_PATH.exists():
            ZIP_PATH.unlink()
        with ZipFile(ZIP_PATH, "w", ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(p for p in stage.rglob("*") if p.is_file()):
                archive.write(path, f"{PACKAGE_NAME}/{path.relative_to(stage).as_posix()}")

        with ZipFile(ZIP_PATH) as archive:
            archive.testzip()
            total_files = sum(not name.endswith("/") for name in archive.namelist())
        print(f"ZIP={ZIP_PATH}")
        print(f"CHECKSUM_ENTRIES={len(lines)}")
        print(f"ZIP_TOTAL_FILES={total_files}")
        print(f"ZIP_SIZE={ZIP_PATH.stat().st_size}")
        print(f"ZIP_SHA256={digest(ZIP_PATH)}")


if __name__ == "__main__":
    main()
