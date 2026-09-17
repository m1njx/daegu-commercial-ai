#!/usr/bin/env python3
"""Phase 24 zero-trust regression and independent-oracle checks."""

from __future__ import annotations

import hashlib
import importlib
import json
import math
import random
import re
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.spatial import distance_matrix
from scipy.stats import rankdata, spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.features.bus_features import load_and_clean_bus_data
from src.recommendation.explain import generate_explanation
from src.recommendation.feature_builder import (
    INDUSTRY_ALIASES,
    build_dong_industry_features,
    resolve_industry_filter,
)
from src.recommendation.improved import calculate_improved_scores, generate_improved_explanation
from src.recommendation.personalization import WEIGHT_PRESETS, validate_and_normalize_weights
from src.recommendation.ranking import rank_locations
from src.recommendation.scoring import calculate_component_scores, compute_total_score
from src.recommendation.transit_enhanced import calculate_enhanced_scores, generate_enhanced_explanation


def load_data():
    base = ROOT / "data/processed"
    dong = pd.read_parquet(base / "feature_mart/commercial_feature_mart_dong.parquet")
    stores = pd.read_parquet(base / "feature_mart/store_spatial_features.parquet")
    bus = pd.read_parquet(base / "transit/bus/daegu_bus_dong_features.parquet")
    return dong, stores, bus


def attach_bus(features: pd.DataFrame, bus: pd.DataFrame) -> pd.DataFrame:
    return features.merge(bus.drop(columns=["adm_nm", "area_km2"]), on="adm_cd2", how="left")


def oracle_pct(values, ascending=True):
    arr = np.asarray(values, dtype=float)
    ranks = rankdata(arr if ascending else -arr, method="average")
    return np.clip(np.round((ranks - 1.0) / (len(arr) - 1.0) * 100.0, 2), 0, 100)


def oracle_components(df: pd.DataFrame, weights: dict[str, float], alpha: float = 0.5):
    demand = np.round(.35*oracle_pct(df.pop_total)+.25*oracle_pct(df.pop_density)+.20*oracle_pct(df.dong_daily_ridership)+.20*oracle_pct(df.total_stores), 2)
    target = np.round(.60*oracle_pct(df.target_ratio)+.40*oracle_pct(df.target_pop), 2)
    raw_comp = np.round(.50*oracle_pct(df.target_pop_per_store)+.50*oracle_pct(df.cat_avg_comp_300m, False), 2)
    unentered = (df.cat_store_count < 1) | (df.total_stores < 30)
    competition = raw_comp.copy(); competition[unentered.to_numpy()] = np.round(competition[unentered.to_numpy()] * alpha, 2)
    subway = np.round(.50*oracle_pct(df.cat_avg_subway_dist, False)+.30*oracle_pct(df.cat_ratio_subway)+.20*oracle_pct(df.dong_daily_ridership), 2)
    bus = np.round(.50*oracle_pct(df.dong_daily_bus_total)+.30*oracle_pct(df.avg_dist_to_bus_m, False)+.20*oracle_pct(df.dong_bus_stop_density), 2)
    access = np.round(.70*subway+.30*bus, 2)
    parking = np.round(.50*oracle_pct(df.cat_avg_parking_300m)+.30*oracle_pct(df.parking_capacity_per_store)+.20*oracle_pct(df.dong_total_parking_capacity), 2)
    industry = oracle_pct(df.location_quotient)
    w = validate_and_normalize_weights(weights)
    total = np.round(w["demand"]*demand+w["target_fit"]*target+w["competition"]*competition+w["accessibility"]*access+w["parking"]*parking+w["industry_fit"]*industry, 2)
    return {"demand_score": demand, "target_fit_score": target, "competition_score": competition,
            "accessibility_score": access, "parking_score": parking, "industry_fit_score": industry,
            "total_score": total, "is_unentered": unentered.to_numpy()}


def scenario(industry, target, preset, dong, stores, bus, alpha=.5):
    feat, meta = build_dong_industry_features(industry, target, dong, stores)
    feat = attach_bus(feat, bus)
    scored = calculate_enhanced_scores(feat, WEIGHT_PRESETS[preset], "candidate_b", True, discount_factor=alpha)
    return feat, rank_locations(scored), meta


def test_01_required_dependencies():
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    for package, module in (("pypdf", "pypdf"), ("reportlab", "reportlab"), ("playwright", "playwright")):
        assert re.search(rf"(?mi)^{package}(?:[<>=!~].*)?$", requirements)
        importlib.import_module(module)


def test_02_raw_data_counts(dong, stores, bus):
    assert len(stores) == 118_357 and len(dong) == 150 and dong.adm_cd2.nunique() == 150
    assert len(bus) == 150 and int(bus.dong_bus_stop_count.sum()) == 3_981
    assert int(dong.dong_parking_lot_count.sum()) == 4_765
    assert int(dong.dong_total_parking_capacity.sum()) == 247_329
    assert int(dong.pop_total.sum()) == 2_347_389


def test_03_data_schema_integrity(dong, stores, bus):
    for frame in (dong, stores, bus):
        assert not frame.empty
        nums = frame.select_dtypes(include=np.number)
        assert np.isfinite(nums.to_numpy(dtype=float)).all()
    assert stores.bizesId.nunique() == len(stores)
    assert not dong.adm_cd2.duplicated().any() and not bus.adm_cd2.duplicated().any()


def test_04_spatial_boundary_integrity():
    gdf = gpd.read_file(ROOT / "data/processed/geojson/대구_행정동_경계_20230701.geojson")
    assert len(gdf) == 150 and gdf.adm_cd2.nunique() == 150 and gdf.crs is not None
    assert gdf.geometry.notna().all() and gdf.geometry.is_valid.all() and (~gdf.geometry.is_empty).all()
    assert any(gdf.adm_nm.str.contains("군위"))


def test_05_bus_source_and_conservation(bus):
    _, _, stats = load_and_clean_bus_data()
    assert stats["loc_total_rows"] == 3_981 and stats["matched_stop_names"] == 3_624
    assert stats["stop_name_match_rate_pct"] == 98.85 and stats["ridership_volume_coverage_pct"] == 99.1
    expected = stats["matched_ridership_volume"] / stats["total_days_in_period"]
    assert math.isclose(bus.dong_daily_bus_total.sum(), expected, abs_tol=1e-8)


def test_06_competition_bruteforce(dong, stores):
    stores = stores.copy()
    stores["indsLclsNm"] = stores["indsLclsNm"].astype(str).str.strip()
    stores["indsMclsNm"] = stores["indsMclsNm"].astype(str).str.strip()
    for query in ("음식점", "학원", "카페", "한식", "숙박"):
        mask, _ = resolve_industry_filter(query, stores)
        selected = stores.loc[mask, ["adm_cd2", "x_utm", "y_utm"]].copy()
        features, _ = build_dong_industry_features(query, "2030", dong, stores)
        for adm in sorted(selected.adm_cd2.unique())[:2]:
            focal = selected[selected.adm_cd2 == adm]
            distances = distance_matrix(focal[["x_utm", "y_utm"]], selected[["x_utm", "y_utm"]])
            oracle = ((distances <= 300.0).sum(axis=1) - 1).mean()
            actual = float(features.loc[features.adm_cd2 == adm, "cat_avg_comp_300m"].iloc[0])
            assert math.isclose(actual, round(float(oracle), 1), abs_tol=.05), (query, adm, oracle, actual)


def test_07_lq_independent_oracle(dong, stores):
    stores = stores.copy()
    stores["indsLclsNm"] = stores["indsLclsNm"].astype(str).str.strip()
    stores["indsMclsNm"] = stores["indsMclsNm"].astype(str).str.strip()
    city_total = len(stores)
    for query in ("카페", "한식", "음식점", "학원", "미용실", "숙박", "종합소매"):
        mask, _ = resolve_industry_filter(query, stores); selected = stores.loc[mask]
        feat, _ = build_dong_industry_features(query, "전체", dong, stores)
        city_share = len(selected) / city_total
        for row in feat.iloc[::31].itertuples():
            expected = 0.0 if row.total_stores == 0 else round((row.cat_store_count / row.total_stores) / city_share, 3)
            assert math.isclose(row.location_quotient, expected, abs_tol=.0005)


def test_08_percentile_oracle():
    from src.recommendation.scoring import to_percentile
    values = pd.Series([0, 1, 1, 5, 9, 9, 10])
    assert np.array_equal(to_percentile(values).to_numpy(), oracle_pct(values))
    assert np.array_equal(to_percentile(values, False).to_numpy(), oracle_pct(values, False))


def test_09_independent_component_oracle(dong, stores, bus):
    demos = [("카페","2030","기본 균형형"),("한식","전체","배후 수요 집중형 (대형 매장/안정형)"),("미용실","2030","기본 균형형"),("학원","10대","타깃 고객 집중형 (트렌디/특화 소비)"),("종합소매","전체","기본 균형형"),("숙박","2030","기본 균형형")]
    for industry, target, preset in demos:
        feat, ranked, _ = scenario(industry,target,preset,dong,stores,bus)
        oracle = oracle_components(feat, WEIGHT_PRESETS[preset])
        actual = ranked.sort_values("adm_cd2")
        order = feat.sort_values("adm_cd2").index.to_numpy()
        for col in ("demand_score","target_fit_score","competition_score","accessibility_score","parking_score","industry_fit_score","total_score"):
            assert np.max(np.abs(actual[col].to_numpy()-np.asarray(oracle[col])[order])) <= .011, (industry,col)


def test_10_alpha_properties(dong, stores, bus):
    feat, _, _ = scenario("숙박","2030","기본 균형형",dong,stores,bus)
    outputs = [calculate_enhanced_scores(feat, discount_factor=a) for a in (.3,.5,.8)]
    entered = feat.cat_store_count.ge(1) & feat.total_stores.ge(30); empty = ~entered
    for col in ("competition_score",):
        assert outputs[0].loc[entered,col].equals(outputs[1].loc[entered,col])
        assert outputs[1].loc[entered,col].equals(outputs[2].loc[entered,col])
    assert (outputs[0].loc[empty,"competition_score"] <= outputs[1].loc[empty,"competition_score"]).all()
    assert (outputs[1].loc[empty,"competition_score"] <= outputs[2].loc[empty,"competition_score"]).all()


def test_11_ranking_invariants(dong, stores, bus):
    _, ranked, _ = scenario("카페","2030","기본 균형형",dong,stores,bus)
    assert ranked["rank"].tolist() == list(range(1,151))
    assert ranked.total_score.between(0,100).all() and ranked.adm_cd2.is_unique
    expected = ranked.sort_values(["total_score","demand_score","target_fit_score","pop_total"], ascending=False)
    assert ranked.adm_cd2.tolist() == expected.adm_cd2.tolist()


def test_12_random_scenario_fuzz(dong, stores, bus):
    rng = random.Random(240916)
    industries = ["카페","한식","미용실","학원","종합소매","숙박","예술·스포츠"]
    targets = ["전체","2030","10대","4050","60대"]
    cache = {}
    for _ in range(100):
        key = (rng.choice(industries), rng.choice(targets))
        if key not in cache:
            feat, _ = build_dong_industry_features(*key, dong, stores); cache[key] = attach_bus(feat,bus)
        raw = {name:rng.random() for name in ("demand","target_fit","competition","accessibility","parking","industry_fit")}
        alpha = rng.choice((.3,.5,.8)); scored = calculate_enhanced_scores(cache[key], raw, discount_factor=alpha)
        ranked = rank_locations(scored); assert len(ranked)==150 and ranked.total_score.between(0,100).all()
        assert np.isfinite(ranked.select_dtypes(include=np.number)).all().all() and ranked.adm_cd2.is_unique


def test_13_direct_input_validation(dong, stores):
    for valid in ("일식", "중식", "음식", "예술·스포츠"):
        feat, _ = build_dong_industry_features(valid,"전체",dong,stores); assert len(feat)==150
    for invalid in ("", "   ", "없는업종XYZ", "!@#$%^&*()"):
        try: build_dong_industry_features(invalid,"전체",dong,stores)
        except ValueError: pass
        else: raise AssertionError(invalid)


def test_14_explanation_grounding(dong, stores, bus):
    demos=[("카페","2030","기본 균형형"),("한식","전체","배후 수요 집중형 (대형 매장/안정형)"),("미용실","2030","기본 균형형"),("학원","10대","타깃 고객 집중형 (트렌디/특화 소비)"),("종합소매","전체","기본 균형형"),("숙박","2030","기본 균형형")]
    banned=("검증된 상권","성공 가능성","성공 확률","높은 성공률","보장","최적지","완벽","미포화 성장 기회","시너지 형성","수익 보장","매출 예측")
    count=0
    for industry,target,preset in demos:
        feat, integrated, meta=scenario(industry,target,preset,dong,stores,bus)
        improved=rank_locations(calculate_improved_scores(feat,WEIGHT_PRESETS[preset]))
        baseline=rank_locations(compute_total_score(calculate_component_scores(feat),WEIGHT_PRESETS[preset]))
        for frame,fn in ((integrated,generate_enhanced_explanation),(improved,generate_improved_explanation),(baseline,generate_explanation)):
            for _,row in frame.head(5).iterrows():
                exp=fn(row,meta); text=" ".join([exp["summary_sentence"],*exp["strengths"],*exp["cautions"]])
                assert not any(word in text for word in banned)
                if row.location_quotient < 1: assert "대구 평균 대비 해당 업종 비중이 상대적으로 높" not in text
                if row.cat_store_count == 0: assert "업종 비중 상대 우위" not in text
                assert str(int(row["rank"])) in exp["summary_sentence"]; count += 1
    assert count==90


def test_15_demo_results_and_spearman(dong, stores, bus):
    expected=[("카페","2030","기본 균형형","신암4동",77.75),("한식","전체","배후 수요 집중형 (대형 매장/안정형)","상인1동",77.47),("미용실","2030","기본 균형형","칠성동",75.45),("학원","10대","타깃 고객 집중형 (트렌디/특화 소비)","범어1동",84.40),("종합소매","전체","기본 균형형","상인1동",72.25),("숙박","2030","기본 균형형","칠성동",75.90)]
    for industry,target,preset,name,score in expected:
        feat, integrated, _=scenario(industry,target,preset,dong,stores,bus)
        subway=rank_locations(calculate_enhanced_scores(feat,WEIGHT_PRESETS[preset],"baseline"))
        top=integrated.iloc[0]; assert top.adm_nm.endswith(name) and float(top.total_score)==score
        joined=integrated[["adm_cd2","rank"]].merge(subway[["adm_cd2","rank"]],on="adm_cd2",suffixes=("_i","_s"))
        rho=spearmanr(joined.rank_i,joined.rank_s).statistic; assert .98 < rho <= 1


def test_16_csv_bom(dong, stores, bus):
    _, ranked, _=scenario("카페","2030","기본 균형형",dong,stores,bus)
    payload=ranked.to_csv(index=False).encode("utf-8-sig")
    assert payload[:3]==b"\xef\xbb\xbf" and "신암4동" in payload.decode("utf-8-sig")


def test_17_ui_state_and_claims():
    app=(ROOT/"app/app.py").read_text(encoding="utf-8")
    block=app[app.index("def apply_demo_scenario"):app.index("# ----------------------------------------------------\n# 3.")]
    assert "discount_factor = 0.50" in block and "filter_unentered = False" in block
    assert "α={discount_factor_val:.2f}" in app and "encode(\"utf-8-sig\")" in app
    assert "검증된 상권" not in app and "iM뱅크 데이터톤" not in app and "Plotly" not in app


def test_18_document_claim_limits():
    paths=[ROOT/"README.md",ROOT/"README_JUDGE.md",ROOT/"docs/MODEL_CARD.md",ROOT/"docs/REPRODUCIBILITY.md",ROOT/"docs/TEST_REPORT.md"]
    for path in paths:
        text=path.read_text(encoding="utf-8")
        assert "사업적" in text and ("성공" in text or "창업 성과" in text)
    combined="\n".join(p.read_text(encoding="utf-8") for p in paths)
    assert "Plotly" not in combined and "2026 AI Blockchain Challenge in Daegu" in combined


def test_19_error_paths(dong, stores, bus):
    feat,_=build_dong_industry_features("카페","2030",dong,stores)
    try: calculate_enhanced_scores(feat, candidate="candidate_b")
    except ValueError as exc: assert "버스 피처" in str(exc)
    else: raise AssertionError("missing bus features did not fail")
    try: rank_locations(pd.DataFrame(), top_n=0)
    except (ValueError, KeyError): pass
    else: raise AssertionError("invalid top_n did not fail")


def test_20_package_and_pdf_manifest():
    manifest=json.loads((ROOT/"submission_manifest.json").read_text(encoding="utf-8"))
    pdf=ROOT/manifest["proposal_pdf_submission"]["path_outside_code_zip"]
    if pdf.is_file():
        assert pdf.suffix.lower()==".pdf"
        assert hashlib.sha256(pdf.read_bytes()).hexdigest()==manifest["proposal_pdf_submission"]["verified_sha256"]
    else:
        assert manifest["proposal_pdf_submission"]["mode"] == "separate_file"
        assert manifest["proposal_pdf_submission"]["verified_pages"] == 5
    assert manifest["proposal_pdf_submission"]["pdf_files_inside_code_zip"]==0


def main():
    dong,stores,bus=load_data()
    tests=[globals()[f"test_{i:02d}_{name}"] for i,name in [
        (1,"required_dependencies"),(2,"raw_data_counts"),(3,"data_schema_integrity"),(4,"spatial_boundary_integrity"),(5,"bus_source_and_conservation"),(6,"competition_bruteforce"),(7,"lq_independent_oracle"),(8,"percentile_oracle"),(9,"independent_component_oracle"),(10,"alpha_properties"),(11,"ranking_invariants"),(12,"random_scenario_fuzz"),(13,"direct_input_validation"),(14,"explanation_grounding"),(15,"demo_results_and_spearman"),(16,"csv_bom"),(17,"ui_state_and_claims"),(18,"document_claim_limits"),(19,"error_paths"),(20,"package_and_pdf_manifest")]]
    for i,test in enumerate(tests,1):
        if i in {1,4,8,17,18,20}: test()
        elif i == 5: test(bus)
        elif i in {2,3}: test(dong,stores,bus)
        elif i in {6,7,13}: test(dong,stores)
        else: test(dong,stores,bus)
        print(f"[PASS] TEST {i:02d}: {test.__name__}")
    print("PHASE 24: 20/20 PASS")


if __name__=="__main__":
    main()
