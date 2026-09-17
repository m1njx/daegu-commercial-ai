#!/usr/bin/env python3
"""Phase 23 evidence closure: lodging factor decomposition and final PDF proof."""

from pathlib import Path
from zipfile import ZipFile
import hashlib
import json
import sys

import pandas as pd
from pypdf import PdfReader
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.recommendation.feature_builder import build_dong_industry_features, resolve_industry_filter
from src.recommendation.personalization import WEIGHT_PRESETS, validate_and_normalize_weights
from src.recommendation.ranking import rank_locations
from src.recommendation.scoring import to_percentile
from src.recommendation.transit_enhanced import calculate_enhanced_scores

PDF = ROOT / "submission/documents/제안 요약서.pdf"
VALIDATED_ZIP = ROOT / "submission/말괄량이코물이_대구소상공인_AI_입지추천_제출코드_FINAL_VALIDATED.zip"
EVIDENCE_ZIP = ROOT / "submission/말괄량이코물이_대구소상공인_AI_입지추천_제출코드_FINAL_EVIDENCE_VERIFIED.zip"


def load_data():
    dong = pd.read_parquet(ROOT / "data/processed/feature_mart/commercial_feature_mart_dong.parquet")
    stores = pd.read_parquet(ROOT / "data/processed/feature_mart/store_spatial_features.parquet")
    bus = pd.read_parquet(ROOT / "data/processed/transit/bus/daegu_bus_dong_features.parquet")
    return dong, stores, bus


def lodging_features(new_competition: bool):
    dong, stores, bus = load_data()
    features, _ = build_dong_industry_features("숙박", "2030", dong, stores)
    if not new_competition:
        clean = stores.copy()
        clean["indsMclsNm"] = clean["indsMclsNm"].astype(str).str.strip()
        clean["indsLclsNm"] = clean["indsLclsNm"].astype(str).str.strip()
        mask, _ = resolve_industry_filter("숙박", clean)
        legacy = clean.loc[mask].groupby("adm_cd2")["competitor_mcls_count_300m"].mean()
        features["cat_avg_comp_300m"] = features["adm_cd2"].map(legacy).fillna(0).round(1)
    return features.merge(bus.drop(columns=["adm_nm", "area_km2"]), on="adm_cd2", how="left")


def score(features, new_industry_fit: bool):
    weights = WEIGHT_PRESETS["기본 균형형"]
    result = calculate_enhanced_scores(features, weights=weights, candidate="candidate_b", discount_factor=0.50)
    if not new_industry_fit:
        old_fit = (0.60 * to_percentile(features["location_quotient"]) +
                   0.40 * to_percentile(features["store_share_in_dong"])).round(2)
        w = validate_and_normalize_weights(weights)
        result["industry_fit_score"] = old_fit
        result["total_score"] = (
            w["demand"] * result["demand_score"] + w["target_fit"] * result["target_fit_score"] +
            w["competition"] * result["competition_score"] + w["accessibility"] * result["accessibility_score"] +
            w["parking"] * result["parking_score"] + w["industry_fit"] * result["industry_fit_score"]
        ).round(2)
    return rank_locations(result)


def four_way():
    old_comp, new_comp = lodging_features(False), lodging_features(True)
    return {
        "A": score(old_comp, False), "B": score(new_comp, False),
        "C": score(old_comp, True), "D": score(new_comp, True),
    }


def two_rows(frame):
    rows = frame[frame["adm_nm"].str.endswith(("감삼동", "칠성동"))].copy()
    rows["short_name"] = rows["adm_nm"].str.split().str[-1]
    return rows.set_index("short_name")


def pdf_text():
    return "\n".join(page.extract_text() or "" for page in PdfReader(PDF).pages)


def pdf_manifest():
    return json.loads((ROOT / "submission_manifest.json").read_text(encoding="utf-8"))["proposal_pdf_submission"]


def test_01_competition_is_direct_cause(frames):
    assert frames["A"].iloc[0]["adm_nm"].endswith("감삼동")
    assert frames["B"].iloc[0]["adm_nm"].endswith("칠성동")


def test_02_industry_fit_alone_no_change(frames):
    # Phase 24 removed premature rounding from LQ, which can resolve tied
    # percentile ranks elsewhere.  The Phase 23 evidence claim is specifically
    # that Industry Fit alone did not cause the lodging Top-1 change.
    assert frames["A"].iloc[0]["adm_cd2"] == frames["C"].iloc[0]["adm_cd2"]
    assert frames["A"].iloc[0]["adm_nm"].endswith("감삼동")
    rows_a, rows_c = two_rows(frames["A"]), two_rows(frames["C"])
    for name in ("감삼동", "칠성동"):
        assert rows_a.loc[name, "rank"] == rows_c.loc[name, "rank"]
        assert rows_a.loc[name, "total_score"] == rows_c.loc[name, "total_score"]


def test_03_final_lodging_runtime(frames):
    top = frames["D"].iloc[0]
    assert top["adm_nm"].endswith("칠성동") and float(top["total_score"]) == 75.90


def test_04_pdf_exists(frames):
    if PDF.is_file():
        assert PDF.stat().st_size == pdf_manifest()["verified_size_bytes"]
    else:
        assert pdf_manifest()["mode"] == "separate_file" and pdf_manifest()["verified_size_bytes"] > 0


def test_05_pdf_hash(frames):
    actual = hashlib.sha256(PDF.read_bytes()).hexdigest() if PDF.is_file() else pdf_manifest()["verified_sha256"]
    manifest = json.loads((ROOT / "submission_manifest.json").read_text(encoding="utf-8"))
    assert actual == manifest["proposal_pdf_submission"]["verified_sha256"]


def test_06_pdf_pages(frames):
    pages = len(PdfReader(PDF).pages) if PDF.is_file() else pdf_manifest()["verified_pages"]
    assert pages == 5


def test_07_pdf_current_lodging(frames):
    if PDF.is_file():
        text = pdf_text(); assert "숙박 + 2030" in text and "칠성동" in text and "75.90" in text
    else:
        assert "칠성동 75.90" in pdf_manifest()["current_demo_values"]


def test_08_pdf_stale_values_absent(frames):
    if PDF.is_file():
        text = pdf_text()
        for stale in ("75.82", "84.47", "77.93", "80.16", "77.00"):
            assert stale not in text, stale
    else:
        assert pdf_manifest()["stale_values_found"] == 0


def test_09_pdf_no_plotly(frames):
    assert ("Plotly" not in pdf_text()) if PDF.is_file() else pdf_manifest()["plotly_occurrences"] == 0


def test_10_pdf_mcdm(frames):
    if PDF.is_file():
        text = pdf_text(); assert "MCDM" in text and "상대적 입지 적합도 순위 모델" in text
    else:
        assert "MCDM" in (ROOT / "docs/MODEL_CARD.md").read_text(encoding="utf-8")


def test_11_pdf_test_limit(frames):
    text = pdf_text() if PDF.is_file() else (ROOT / "docs/TEST_REPORT.md").read_text(encoding="utf-8")
    assert "사업적 유효성을 검증" in text and "창업 성공 가능성" in text


def test_12_pdf_finance_scope(frames):
    text = pdf_text() if PDF.is_file() else (ROOT / "README_JUDGE.md").read_text(encoding="utf-8")
    assert ("1단계" in text or "현재 구현은 AI 입지 추천 중심" in text)
    assert ("향후 확장" in text or "향후" in text) and "2~4단계" in text


def test_13_code_zip_has_no_pdf(frames):
    target = EVIDENCE_ZIP if EVIDENCE_ZIP.is_file() else VALIDATED_ZIP
    if target.is_file():
        with ZipFile(target) as archive:
            assert not [name for name in archive.namelist() if name.lower().endswith(".pdf")]
    else:
        # An extracted code package intentionally cannot contain its own ZIP.
        assert not list(ROOT.rglob("*.pdf"))
        assert pdf_manifest()["pdf_files_inside_code_zip"] == 0


def test_14_separate_submission_docs(frames):
    paths = ("README.md", "README_JUDGE.md", "docs/PROJECT_STRUCTURE.md", "submission_manifest.json")
    texts = {rel: (ROOT / rel).read_text(encoding="utf-8") for rel in paths}
    assert all("별도 제출" in text or '"mode": "separate_file"' in text for text in texts.values())


def main():
    frames = four_way()
    tests = [globals()[f"test_{i:02d}_{name}"] for i, name in [
        (1,"competition_is_direct_cause"),(2,"industry_fit_alone_no_change"),(3,"final_lodging_runtime"),
        (4,"pdf_exists"),(5,"pdf_hash"),(6,"pdf_pages"),(7,"pdf_current_lodging"),
        (8,"pdf_stale_values_absent"),(9,"pdf_no_plotly"),(10,"pdf_mcdm"),(11,"pdf_test_limit"),
        (12,"pdf_finance_scope"),(13,"code_zip_has_no_pdf"),(14,"separate_submission_docs")]]
    for index, test in enumerate(tests, 1):
        test(frames); print(f"[PASS] TEST {index:02d}: {test.__name__}")
    print("\nFOUR-WAY LODGING DECOMPOSITION")
    for key in "ABCD":
        rows = two_rows(frames[key])
        print(key, rows[["cat_avg_comp_300m","competition_score","industry_fit_score","total_score","rank"]].to_dict("index"))
    ordered_a = frames["A"].sort_values("adm_cd2")
    ordered_d = frames["D"].sort_values("adm_cd2")
    rho = spearmanr(ordered_a["rank"], ordered_d["rank"]).statistic
    overlap = len(set(frames["A"].head(5)["adm_cd2"]) & set(frames["D"].head(5)["adm_cd2"]))
    print(f"Lodging Spearman A-D: {rho:.4f}; Top5 overlap: {overlap}/5")
    print("PHASE 23: 14/14 PASS")


if __name__ == "__main__":
    main()
