#!/usr/bin/env python3
"""Phase 25 final document, PDF and package consistency checks."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.recommendation.feature_builder import build_dong_industry_features
from src.recommendation.personalization import WEIGHT_PRESETS
from src.recommendation.ranking import rank_locations
from src.recommendation.transit_enhanced import calculate_enhanced_scores

PDF = ROOT / "submission/documents/제안 요약서.pdf"
ZIP = ROOT / "submission/말괄량이코물이_대구소상공인_AI_입지추천_제출코드_FINAL_SUBMISSION.zip"
EXPECTED_COUNTS = [10, 12, 10, 10, 10, 6, 12, 12, 7, 14, 14, 15, 18, 14, 20, 14, 15]
EXPECTED_TOTAL = sum(EXPECTED_COUNTS)


def pdf_text() -> str:
    if PDF.is_file():
        return "\n".join(page.extract_text() or "" for page in PdfReader(PDF).pages)
    return (ROOT / "scripts/build_phase22_proposal_pdf.py").read_text(encoding="utf-8")


def pdf_manifest() -> dict:
    manifest = json.loads((ROOT / "submission_manifest.json").read_text(encoding="utf-8"))
    return manifest["proposal_pdf_submission"]


def runtime_demos():
    base = ROOT / "data/processed"
    dong = pd.read_parquet(base / "feature_mart/commercial_feature_mart_dong.parquet")
    stores = pd.read_parquet(base / "feature_mart/store_spatial_features.parquet")
    bus = pd.read_parquet(base / "transit/bus/daegu_bus_dong_features.parquet")
    demos = [
        ("카페", "2030", "기본 균형형"),
        ("한식", "전체", "배후 수요 집중형 (대형 매장/안정형)"),
        ("미용실", "2030", "기본 균형형"),
        ("학원", "10대", "타깃 고객 집중형 (트렌디/특화 소비)"),
        ("종합소매", "전체", "기본 균형형"),
        ("숙박", "2030", "기본 균형형"),
    ]
    results = []
    for industry, target, preset in demos:
        features, _ = build_dong_industry_features(industry, target, dong, stores)
        features = features.merge(bus.drop(columns=["adm_nm", "area_km2"]), on="adm_cd2", how="left")
        ranked = rank_locations(calculate_enhanced_scores(features, WEIGHT_PRESETS[preset]))
        results.append((industry, target, ranked.iloc[0]["adm_nm"].split()[-1], float(ranked.iloc[0]["total_score"])))
    return results


def test_01_project_structure_total():
    text = (ROOT / "docs/PROJECT_STRUCTURE.md").read_text(encoding="utf-8")
    assert f"{EXPECTED_TOTAL}개" in text and "17개 테스트 스위트" in text


def test_02_project_structure_no_stale_current_total():
    text = (ROOT / "docs/PROJECT_STRUCTURE.md").read_text(encoding="utf-8")
    assert "Phase 6~21 132개와 Phase 22 18개, 총 150개" not in text
    assert "TEST_REPORT.md                 # 150개 전체 회귀" not in text


def test_03_suite_inventory_matches_manifest():
    manifest = json.loads((ROOT / "submission_manifest.json").read_text(encoding="utf-8"))
    counts = [suite["tests"] for suite in manifest["tests"]["suites"].values()]
    assert counts == EXPECTED_COUNTS and len(counts) == 17
    assert sum(counts) == manifest["tests"]["total"] == EXPECTED_TOTAL


def test_04_pdf_exists_and_pages():
    if PDF.is_file():
        assert len(PdfReader(PDF).pages) == 5
    else:
        assert pdf_manifest()["mode"] == "separate_file" and pdf_manifest()["verified_pages"] == 5


def test_05_pdf_heading_current():
    text = pdf_text()
    assert "Phase 22 최종 공식 데모" not in text
    assert "최종 공식 데모 결과" in text


def test_06_pdf_runtime_demo_values():
    text = pdf_text()
    for _, _, dong, score in runtime_demos():
        assert dong in text and f"{score:.2f}" in text


def test_07_pdf_retail_and_lodging():
    results = runtime_demos()
    assert results[4][2:] == ("상인1동", 72.25)
    assert results[5][2:] == ("칠성동", 75.90)


def test_08_pdf_stale_values_absent():
    text = pdf_text()
    for stale in ("77.93", "80.16", "77.00", "84.47", "감삼동 75.82"):
        assert stale not in text


def test_09_pdf_stack_truthful():
    assert "Plotly" not in pdf_text()


def test_10_pdf_test_total():
    text = pdf_text()
    assert f"17개 스위트 {EXPECTED_TOTAL}/{EXPECTED_TOTAL} PASS" in text


def test_11_docs_test_total_consistency():
    paths = [ROOT/"README.md", ROOT/"README_JUDGE.md", ROOT/"docs/MODEL_CARD.md",
             ROOT/"docs/REPRODUCIBILITY.md", ROOT/"docs/TEST_REPORT.md", ROOT/"docs/PROJECT_STRUCTURE.md"]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert str(EXPECTED_TOTAL) in text, path


def test_12_model_results_regression():
    expected = [("신암4동",77.75),("상인1동",77.47),("칠성동",75.45),
                ("범어1동",84.40),("상인1동",72.25),("칠성동",75.90)]
    assert [(dong, score) for _, _, dong, score in runtime_demos()] == expected


def test_13_package_structure():
    if not ZIP.is_file():
        package_source = (ROOT / "scripts/package_phase22.py").read_text(encoding="utf-8")
        assert ZIP.name in package_source
        return
    with ZipFile(ZIP) as archive:
        files = [item.filename for item in archive.infolist() if not item.is_dir()]
        assert not any(name.lower().endswith(".pdf") for name in files)
        assert any(name.endswith("scripts/run_phase25_final_document_closure.py") for name in files)
        assert any(name.endswith("scripts/run_final_defect_closure_tests.py") for name in files)


def test_14_pdf_separate_submission_contract():
    for path in (ROOT/"README.md", ROOT/"docs/PROJECT_STRUCTURE.md"):
        text = path.read_text(encoding="utf-8")
        assert "별도 제출" in text
    assert json.loads((ROOT/"submission_manifest.json").read_text(encoding="utf-8"))["proposal_pdf_submission"]["mode"] == "separate_file"


def main():
    tests = [globals()[f"test_{index:02d}_{name}"] for index, name in enumerate([
        "project_structure_total", "project_structure_no_stale_current_total", "suite_inventory_matches_manifest",
        "pdf_exists_and_pages", "pdf_heading_current", "pdf_runtime_demo_values", "pdf_retail_and_lodging",
        "pdf_stale_values_absent", "pdf_stack_truthful", "pdf_test_total", "docs_test_total_consistency",
        "model_results_regression", "package_structure", "pdf_separate_submission_contract"], 1)]
    for index, test in enumerate(tests, 1):
        test(); print(f"[PASS] TEST {index:02d}: {test.__name__}")
    print(f"PHASE 25: {len(tests)}/{len(tests)} PASS")


if __name__ == "__main__":
    main()
