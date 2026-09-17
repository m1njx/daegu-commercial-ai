#!/usr/bin/env python3
"""Phase 21 regression suite for the eleven reproduced final defects."""

from __future__ import annotations

import ast
import math
import sys
import tempfile
import unicodedata
from pathlib import Path

import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import src.features.bus_features as bus_features
from src.recommendation.explain import generate_explanation
from src.recommendation.feature_builder import build_dong_industry_features
from src.recommendation.personalization import WEIGHT_PRESETS
from src.recommendation.ranking import rank_locations
from src.recommendation.transit_enhanced import calculate_enhanced_scores

BUS_COLS = [
    "dong_bus_stop_count", "dong_daily_bus_boarding", "dong_daily_bus_alighting",
    "dong_daily_bus_total", "dong_bus_stop_density", "dong_bus_ridership_per_stop",
    "avg_dist_to_bus_m", "ratio_stores_in_bus_300m",
]
DEMOS = (
    ("카페", "2030", "기본 균형형", "신암4동", 77.75),
    ("한식", "전체", "배후 수요 집중형 (대형 매장/안정형)", "상인1동", 77.47),
    ("미용실", "2030", "기본 균형형", "칠성동", 75.45),
    ("학원", "10대", "타깃 고객 집중형 (트렌디/특화 소비)", "범어1동", 84.40),
    ("종합소매", "전체", "기본 균형형", "상인1동", 72.25),
    ("숙박", "2030", "기본 균형형", "칠성동", 75.90),
)


def function_source(text: str, name: str) -> str:
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(text, node) or ""
    raise AssertionError(f"function not found: {name}")


def main() -> None:
    app_text = (ROOT / "app/app.py").read_text(encoding="utf-8")
    docs = {
        path: (ROOT / path).read_text(encoding="utf-8")
        for path in (
            "README.md", "README_JUDGE.md", "docs/MODEL_CARD.md",
            "docs/REPRODUCIBILITY.md", "docs/TEST_REPORT.md",
            "docs/DATA_SOURCES.md", "docs/PROJECT_STRUCTURE.md",
        )
    }
    mart = pd.read_parquet(ROOT / "data/processed/feature_mart/commercial_feature_mart_dong.parquet")
    stores = pd.read_parquet(ROOT / "data/processed/feature_mart/store_spatial_features.parquet")
    bus = pd.read_parquet(ROOT / "data/processed/transit/bus/daegu_bus_dong_features.parquet")
    for col in BUS_COLS:
        mart[col] = bus[col].values
    passed = 0

    # 1. The exact download payload is bytes with the UTF-8-SIG BOM.
    assert '.to_csv(index=False).encode("utf-8-sig")' in app_text
    payload = pd.DataFrame({"행정동명": ["신암4동"]}).to_csv(index=False).encode("utf-8-sig")
    assert payload[:3] == b"\xef\xbb\xbf" and "신암4동" in payload.decode("utf-8-sig")
    passed += 1

    # 2. requirements matches the first Streamlit release supporting dataframe stretch width.
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "streamlit>=1.49.0" in requirements and "streamlit>=1.33.0" not in requirements
    passed += 1

    # 3. The unused card renderer and its stale section heading are removed.
    assert "render_sub_rank_card" not in app_text and "SECTION 3: 🥈 2위 ~ 5위" not in app_text
    passed += 1

    # 4. Demo 4 label is grounded in the current feature row.
    feat_academy, _ = build_dong_industry_features("학원", "10대", mart, stores)
    row_academy = feat_academy.loc[feat_academy["adm_nm"].str.endswith("범어1동")].iloc[0]
    assert math.isclose(float(row_academy["location_quotient"]), 1.902, abs_tol=0.0005)
    assert "학원 특화도 LQ 1.90" in app_text and "학원가 LQ 2.37" not in app_text
    passed += 1

    # 5. Recompute all six demo correlations and require docs to state the true range.
    correlations = []
    for industry, target, preset, expected_dong, expected_score in DEMOS:
        feat, _ = build_dong_industry_features(industry, target, mart, stores)
        for col in BUS_COLS:
            feat[col] = mart[col].values
        kwargs = {"weights": WEIGHT_PRESETS[preset], "is_improved": True, "discount_factor": 0.50}
        subway = rank_locations(calculate_enhanced_scores(feat, candidate="baseline", **kwargs))
        integrated = rank_locations(calculate_enhanced_scores(feat, candidate="candidate_b", **kwargs))
        merged = subway[["adm_cd2", "rank"]].merge(
            integrated[["adm_cd2", "rank"]], on="adm_cd2", suffixes=("_subway", "_integrated")
        )
        correlations.append(float(spearmanr(merged["rank_subway"], merged["rank_integrated"]).statistic))
        assert integrated.iloc[0]["adm_nm"].endswith(expected_dong)
        assert math.isclose(float(integrated.iloc[0]["total_score"]), expected_score, abs_tol=0.06)
    assert f"{min(correlations):.4f} ~ {max(correlations):.4f}" == "0.9915 ~ 0.9969"
    for path in ("README.md", "README_JUDGE.md", "docs/MODEL_CARD.md", "docs/REPRODUCIBILITY.md"):
        assert "0.9915" in docs[path] and "0.9969" in docs[path]
    passed += 1

    # 6. Spearman caption is a value-dependent function with all three branches.
    source = function_source(app_text, "describe_rank_similarity")
    namespace: dict[str, object] = {}
    exec(source, namespace)
    describe = namespace["describe_rank_similarity"]
    assert describe(0.99) == "높은 순위 유사도"
    assert "일부 순위 변화" in describe(0.9757)
    assert describe(0.90) == "순위 변화 확인 필요"
    assert 'describe_rank_similarity(float(rho))' in app_text
    passed += 1

    # 7. Tab 5 count and download label use the filtered result length.
    assert "result_count = len(active_ranked)" in app_text
    assert "현재 조건 랭킹 데이터 {result_count}개" in app_text
    assert "현재 조건 {result_count}개 행정동 추천 데이터 CSV 다운로드" in app_text
    passed += 1

    # 8. Rail and bus periods are explicitly distinguished by source granularity.
    assert "도시철도는 2026년 1~7월 일별 관측(212일)" in app_text
    assert "시내버스는 같은 기간의 월별 집계를 212일로 나눈 일평균" in app_text
    passed += 1

    # 9. Demo 6 does not describe Gamsam-dong itself as a zero-store case.
    assert "숙박업 후보지 및 점포 미확인 지역 보정 비교" in app_text
    assert "감삼동 1위 / 0점포 왜곡 방어 실증" not in app_text
    feat_lodging, _ = build_dong_industry_features("숙박", "2030", mart, stores)
    gamsam = feat_lodging.loc[feat_lodging["adm_nm"].str.endswith("감삼동")].iloc[0]
    assert int(gamsam["cat_store_count"]) == 6
    passed += 1

    # 10. Baseline explanation cannot claim LQ synergy for a zero-store row.
    zero_row = pd.Series({
        "adm_nm": "대구광역시 테스트동", "rank": 1, "total_score": 80,
        "industry_fit_score": 99, "location_quotient": 9.9, "cat_store_count": 0,
        "target_fit_score": 0, "accessibility_score": 50, "demand_score": 50,
        "competition_score": 50, "parking_score": 50,
    })
    explanation = generate_explanation(zero_row, {"industry_label": "숙박", "target_demographic_label": "2030"})
    assert all("동종 업종 시너지" not in text for text in explanation["strengths"])
    passed += 1

    # 11. Raw-file discovery is deterministic and rejects ambiguous exact-period inputs.
    original_dir = bus_features.RAW_BUS_DIR
    try:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            loc = root / unicodedata.normalize("NFD", "대구 시내버스 정류소 위치정보.csv")
            loc.write_text("정류소명\nA\n", encoding="utf-8")
            rid_dir = root / unicodedata.normalize("NFD", "대구 시내버스 정류소별 이용자수")
            rid_dir.mkdir()
            expected = rid_dir / "시내버스 정류소별 월별 이용자수(2026-01~07).csv"
            expected.write_text("정류소명,합계\nA,1\n", encoding="utf-8")
            (rid_dir / "시내버스 정류소별 월별 이용자수(2025년).csv").write_text("x\n", encoding="utf-8")
            bus_features.RAW_BUS_DIR = root
            found_loc, found_rid = bus_features.find_bus_raw_files()
            assert found_loc == loc and found_rid == expected
            duplicate_dir = root / "또다른 정류소별 이용자수"
            duplicate_dir.mkdir()
            (duplicate_dir / expected.name).write_text("x\n", encoding="utf-8")
            try:
                bus_features.find_bus_raw_files()
                raise AssertionError("ambiguous ridership candidates were silently accepted")
            except RuntimeError as exc:
                assert "후보가 여러 개" in str(exc)
    finally:
        bus_features.RAW_BUS_DIR = original_dir
    passed += 1

    # 12. Phase 20 spatial clustering and total-conservation invariants remain intact.
    stops = pd.read_parquet(ROOT / "data/processed/transit/bus/daegu_bus_stops_processed.parquet")
    dongs = pd.read_parquet(ROOT / "data/processed/transit/bus/daegu_bus_dong_features.parquet")
    _, _, metadata = bus_features.load_and_clean_bus_data()
    assert all(stops.loc[stops["정류소명"] == name, "stop_cluster_id"].nunique() > 1 for name in ("달산1리", "달산2리", "수서2리"))
    expected_daily = metadata["matched_ridership_volume"] / bus_features.TOTAL_PERIOD_DAYS_2026
    assert math.isclose(float(stops["pole_daily_total"].sum()), expected_daily, abs_tol=1e-8)
    assert math.isclose(float(dongs["dong_daily_bus_total"].sum()), expected_daily, abs_tol=1e-8)
    passed += 1

    # 13. Judge-facing documents contain none of the superseded defect literals.
    combined_docs = "\n".join(docs.values())
    for stale in ("0.9894", "0.9943", "학원가 LQ 2.37", "FINAL_v3", "FINAL_INTERACTIVE", "FINAL_COMPAT", "FINAL_CONSISTENT"):
        assert stale not in combined_docs, stale
    passed += 1

    # 14. The six demo labels remain grounded in current top-one names and key facts.
    for label in ("신암4동 1위", "상인1동 1위", "칠성동 1위", "범어1동 1위"):
        assert label in app_text
    assert "LQ 1.90" in app_text and "0점포 왜곡 방어 실증" not in app_text
    passed += 1

    # 15. Manifest test accounting includes this complete suite exactly once.
    import json
    manifest = json.loads((ROOT / "submission_manifest.json").read_text(encoding="utf-8"))
    suites = manifest["tests"]["suites"]
    assert suites["phase21"]["tests"] == 15 and suites["phase21"]["passed"] == 15
    assert sum(suite["tests"] for suite in suites.values()) == manifest["tests"]["total"]
    assert manifest["tests"]["total"] == manifest["tests"]["passed"]
    passed += 1

    assert passed == 15
    print("PHASE 21: 15/15 PASS")


if __name__ == "__main__":
    main()
