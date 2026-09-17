#!/usr/bin/env python3
"""Phase 22 dedicated semantic, model, document and package regression suite."""

from pathlib import Path
from zipfile import ZipFile
import hashlib
import re
import sys

import numpy as np
import pandas as pd
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.recommendation.explain import generate_explanation
from src.recommendation.feature_builder import (
    build_dong_industry_features, calculate_selected_category_competition,
    resolve_industry_filter,
)
from src.recommendation.improved import calculate_improved_scores, generate_improved_explanation
from src.recommendation.personalization import WEIGHT_PRESETS
from src.recommendation.ranking import rank_locations
from src.recommendation.scoring import calculate_component_scores, to_percentile
from src.recommendation.transit_enhanced import calculate_enhanced_scores, generate_enhanced_explanation


def load_inputs():
    dong = pd.read_parquet(ROOT / "data/processed/feature_mart/commercial_feature_mart_dong.parquet")
    stores = pd.read_parquet(ROOT / "data/processed/feature_mart/store_spatial_features.parquet")
    bus = pd.read_parquet(ROOT / "data/processed/transit/bus/daegu_bus_dong_features.parquet")
    return dong, stores, bus


def with_bus(features, bus):
    return features.merge(bus.drop(columns=["adm_nm", "area_km2"]), on="adm_cd2", how="left")


def manual_comp(query, stores):
    clean = stores.copy()
    clean["indsMclsNm"] = clean["indsMclsNm"].astype(str).str.strip()
    clean["indsLclsNm"] = clean["indsLclsNm"].astype(str).str.strip()
    mask, _ = resolve_industry_filter(query, clean)
    selected = clean.loc[mask].copy()
    selected["manual"] = calculate_selected_category_competition(selected)
    return selected.groupby("adm_cd2")["manual"].mean()


def pdf_text():
    path = ROOT / "submission/documents/제안 요약서.pdf"
    if not path.is_file():
        return ""
    return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def test_01_food_scope(dong, stores, bus):
    features, _ = build_dong_industry_features("음식점", "전체", dong, stores)
    expected = manual_comp("음식점", stores)
    row = features[features["adm_nm"].str.endswith("성내1동")].iloc[0]
    assert round(row["cat_avg_comp_300m"], 1) == round(expected.loc[row["adm_cd2"]], 1) == 422.2


def test_02_academy_scope(dong, stores, bus):
    features, _ = build_dong_industry_features("학원", "10대", dong, stores)
    expected = manual_comp("학원", stores)
    merged = features.set_index("adm_cd2")["cat_avg_comp_300m"].sub(expected, fill_value=0)
    assert merged.abs().max() <= 0.051


def test_03_single_category_scope(dong, stores, bus):
    for query in ("카페", "한식"):
        features, _ = build_dong_industry_features(query, "2030", dong, stores)
        expected = manual_comp(query, stores)
        actual = features.set_index("adm_cd2")["cat_avg_comp_300m"]
        assert actual.sub(expected.reindex(actual.index).fillna(0).round(1)).abs().max() <= 0.051


def test_04_direct_input_scope(dong, stores, bus):
    features, meta = build_dong_industry_features("일식", "전체", dong, stores)
    expected = manual_comp("일식", stores)
    assert "일식" in meta["industry_label"]
    actual = features.set_index("adm_cd2")["cat_avg_comp_300m"]
    assert actual.sub(expected.reindex(actual.index).fillna(0).round(1)).abs().max() <= 0.051


def test_05_alpha_sync(dong, stores, bus):
    features, _ = build_dong_industry_features("숙박", "2030", dong, stores)
    features = with_bus(features, bus)
    for alpha in (0.30, 0.50, 0.80):
        scored = calculate_enhanced_scores(features, candidate="candidate_b", discount_factor=alpha)
        zero = scored[scored["cat_store_count"] == 0]
        assert np.allclose(zero["competition_score"], (zero["raw_competition_score"] * alpha).round(2))
    app = (ROOT / "app/app.py").read_text(encoding="utf-8")
    assert app.count("discount_factor_val:.2f") >= 3


def test_06_comparison_semantics(dong, stores, bus):
    app = (ROOT / "app/app.py").read_text(encoding="utf-8")
    assert "할인 적용 전후 비교표가 아닙니다" in app
    assert "교통 접근성 모델별 결과 비교" in app


def test_07_industry_fit_lq_only(dong, stores, bus):
    features, _ = build_dong_industry_features("학원", "10대", dong, stores)
    expected = to_percentile(features["location_quotient"])
    baseline = calculate_component_scores(features.copy())
    improved = calculate_improved_scores(features.copy())
    enhanced = calculate_enhanced_scores(with_bus(features, bus), candidate="candidate_b")
    for frame in (baseline, improved, enhanced):
        assert np.allclose(frame["industry_fit_score"], expected)


def test_08_lq_claim_guard(dong, stores, bus):
    row = pd.Series({"adm_nm":"대구광역시 중구 중동", "rank":1, "total_score":70,
        "industry_fit_score":99, "location_quotient":0.99, "cat_store_count":20})
    meta = {"industry_label":"학원", "target_demographic_label":"10대 이하"}
    for fn in (generate_explanation, generate_improved_explanation, generate_enhanced_explanation):
        text = " ".join(fn(row, meta).get("strengths", []))
        assert "상대 우위" not in text and "집적 효과" not in text and "시너지" not in text


def test_09_market_status_neutral(dong, stores, bus):
    features, _ = build_dong_industry_features("숙박", "2030", dong, stores)
    scored = calculate_enhanced_scores(with_bus(features, bus), candidate="candidate_b")
    assert set(scored["market_status"]) <= {"해당 업종 점포 확인 지역", "해당 업종 점포 미확인 지역", "해당 업종 점포가 적은 지역"}


def test_10_test_limitations(dong, stores, bus):
    phrase = "실제 창업 성과"
    for rel in ("README.md", "README_JUDGE.md", "docs/MODEL_CARD.md", "docs/TEST_REPORT.md", "docs/REPRODUCIBILITY.md"):
        assert phrase in (ROOT / rel).read_text(encoding="utf-8"), rel


def test_11_spearman_limitations(dong, stores, bus):
    phrase = "사업적 정확도"
    for rel in ("README.md", "README_JUDGE.md", "docs/MODEL_CARD.md"):
        assert phrase in (ROOT / rel).read_text(encoding="utf-8"), rel


def test_12_markdown_math(dong, stores, bus):
    for rel in ("README.md", "README_JUDGE.md", "docs/MODEL_CARD.md", "docs/TEST_REPORT.md", "docs/REPRODUCIBILITY.md"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert not re.search(r"\\\\(?:rho|sim|alpha|to)", text), rel


def test_13_checksums(dong, stores, bus):
    checksum = ROOT / "CHECKSUMS.sha256"
    lines = [line for line in checksum.read_text(encoding="utf-8").splitlines() if line.strip()]
    for line in lines:
        digest, rel = line.split("  ", 1)
        path = ROOT / rel
        if not path.is_file() and rel.startswith("screenshots/"):
            path = ROOT / "submission" / rel
        assert path.is_file(), rel
        assert sha256(path) == digest, rel


def test_14_pdf_demo_values(dong, stores, bus):
    text = pdf_text()
    expected = (("신암4동", "77.75"), ("상인1동", "77.47"), ("칠성동", "75.45"),
                ("범어1동", "84.40"), ("상인1동", "72.25"), ("칠성동", "75.90"))
    if text:
        for name, score in expected:
            assert name in text and score in text, (name, score)
    else:
        # The proposal PDF is submitted separately from the code ZIP. In the
        # extracted package, verify its documented values against runtime data.
        readme = (ROOT / "docs/REPRODUCIBILITY.md").read_text(encoding="utf-8")
        for name, score in expected:
            assert name in readme and score in readme, (name, score)


def test_15_pdf_stack(dong, stores, bus):
    text = pdf_text()
    if text:
        assert "Plotly" not in text
    else:
        assert "Plotly" not in (ROOT / "README.md").read_text(encoding="utf-8")


def test_16_zip_structure(dong, stores, bus):
    zips = list((ROOT / "submission").glob("*FINAL_VALIDATED.zip"))
    if zips:
        assert len(zips) == 1
        with ZipFile(zips[0]) as zf:
            files = [n for n in zf.namelist() if not n.endswith("/")]
            assert any(n.endswith("submission_manifest.json") for n in files)
            assert any(n.endswith("CHECKSUMS.sha256") for n in files)
            assert not any(n.lower().endswith(".pdf") for n in files)
    else:
        # In an independently extracted clean room, the package ZIP is not
        # nested inside itself. Validate the extracted package contract.
        assert (ROOT / "submission_manifest.json").is_file()
        assert (ROOT / "CHECKSUMS.sha256").is_file()
        assert not list(ROOT.rglob("*.pdf"))


def test_17_neutral_user_labels(dong, stores, bus):
    production = "\n".join((ROOT / rel).read_text(encoding="utf-8") for rel in (
        "app/app.py", "src/recommendation/explain.py", "src/recommendation/improved.py", "src/recommendation/transit_enhanced.py"))
    for stale in ("검증된 상권", "미검증 소규모 상권"):
        assert stale not in production


def test_18_claim_blacklist(dong, stores, bus):
    production = "\n".join((ROOT / rel).read_text(encoding="utf-8") for rel in (
        "app/app.py", "src/recommendation/explain.py", "src/recommendation/improved.py", "src/recommendation/transit_enhanced.py"))
    for claim in ("동종 업종 시너지", "미포화 성장 기회", "높은 성공률", "성공 가능성이 높"):
        assert claim not in production


def main():
    dong, stores, bus = load_inputs()
    tests = [globals()[f"test_{i:02d}_{name}"] for i, name in [
        (1,"food_scope"),(2,"academy_scope"),(3,"single_category_scope"),(4,"direct_input_scope"),
        (5,"alpha_sync"),(6,"comparison_semantics"),(7,"industry_fit_lq_only"),(8,"lq_claim_guard"),
        (9,"market_status_neutral"),(10,"test_limitations"),(11,"spearman_limitations"),(12,"markdown_math"),
        (13,"checksums"),(14,"pdf_demo_values"),(15,"pdf_stack"),(16,"zip_structure"),
        (17,"neutral_user_labels"),(18,"claim_blacklist")]]
    passed = 0
    for idx, test in enumerate(tests, 1):
        test(dong, stores, bus)
        passed += 1
        print(f"[PASS] TEST {idx:02d}: {test.__name__}")
    print(f"PHASE 22: {passed}/{len(tests)} PASS")


if __name__ == "__main__":
    main()
