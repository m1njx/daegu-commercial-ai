#!/usr/bin/env python3
"""Phase 19 cross-layer consistency regression suite."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.recommendation.explain import generate_explanation
from src.recommendation.feature_builder import build_dong_industry_features
from src.recommendation.improved import generate_improved_explanation
from src.recommendation.personalization import BASELINE_WEIGHTS, WEIGHT_PRESETS
from src.recommendation.ranking import rank_locations
from src.recommendation.scoring import calculate_component_scores, compute_total_score
from src.recommendation.transit_enhanced import calculate_enhanced_scores, generate_enhanced_explanation

OFFICIAL_COMPETITION = "2026 AI Blockchain Challenge in Daegu"
TEAM = "말괄량이코물이"
SORT_KEYS = ["total_score", "demand_score", "target_fit_score", "pop_total"]
BUS_COLS = [
    "dong_bus_stop_count", "dong_daily_bus_boarding", "dong_daily_bus_alighting",
    "dong_daily_bus_total", "dong_bus_stop_density", "dong_bus_ridership_per_stop",
    "avg_dist_to_bus_m", "ratio_stores_in_bus_300m",
]


def package_root() -> Path:
    if (ROOT / "submission_manifest.json").is_file():
        return ROOT
    matches = sorted((ROOT / "submission" / "package").glob("*/submission_manifest.json"))
    assert len(matches) == 1
    return matches[0].parent


def assigned_literal(tree: ast.AST, name: str):
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError(f"{name} not found")


def assigned_list_length(tree: ast.AST, name: str) -> int:
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            assert isinstance(node.value, (ast.List, ast.Tuple))
            return len(node.value.elts)
    raise AssertionError(f"{name} not found")


def assigned_dict_length(tree: ast.AST, name: str) -> int:
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            assert isinstance(node.value, ast.Dict)
            return len(node.value.keys)
    raise AssertionError(f"{name} not found")


def function_source(text: str, tree: ast.AST, name: str) -> str:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return ast.get_source_segment(text, node) or ""
    raise AssertionError(f"{name} not found")


def load_inputs():
    dong = pd.read_parquet(ROOT / "data/processed/feature_mart/commercial_feature_mart_dong.parquet")
    store = pd.read_parquet(ROOT / "data/processed/feature_mart/store_spatial_features.parquet")
    bus = pd.read_parquet(ROOT / "data/processed/transit/bus/daegu_bus_dong_features.parquet")
    for col in BUS_COLS:
        dong[col] = bus[col].values
    return dong, store


def score_three_models(dong, store, industry, target, weights):
    feat, meta = build_dong_industry_features(industry, target, dong, store)
    for col in BUS_COLS:
        feat[col] = dong[col].values
    baseline = rank_locations(compute_total_score(calculate_component_scores(feat.copy()), weights))
    improved = rank_locations(calculate_enhanced_scores(
        feat.copy(), weights=weights, candidate="baseline", is_improved=True,
        min_stores=1, discount_factor=0.50,
    ))
    integrated = rank_locations(calculate_enhanced_scores(
        feat.copy(), weights=weights, candidate="candidate_b", is_improved=True,
        min_stores=1, discount_factor=0.50,
    ))
    return {"Baseline": baseline, "Improved": improved, "Integrated": integrated}, meta


def main() -> None:
    app_path = ROOT / "app/app.py"
    app_text = app_path.read_text(encoding="utf-8")
    tree = ast.parse(app_text)
    pkg = package_root()
    readme = (pkg / "README.md").read_text(encoding="utf-8")
    judge = (pkg / "README_JUDGE.md").read_text(encoding="utf-8")
    reproducibility = (pkg / "docs/REPRODUCIBILITY.md").read_text(encoding="utf-8")
    model_card = (pkg / "docs/MODEL_CARD.md").read_text(encoding="utf-8")
    manifest = json.loads((pkg / "submission_manifest.json").read_text(encoding="utf-8"))

    print("=" * 72)
    print("PHASE 19: Cross-Layer Consistency 14 Tests")
    print("=" * 72)

    selector = function_source(app_text, tree, "generate_active_explanation")
    assert "if is_integrated_mode" in selector and "generate_enhanced_explanation(row, meta)" in selector
    print("[PASS] 1 Integrated explanation branch -> enhanced")
    assert "if is_improved_mode" in selector and "generate_improved_explanation(row, meta)" in selector
    print("[PASS] 2 Improved explanation branch -> improved")
    assert "return generate_explanation(row, meta)" in selector
    print("[PASS] 3 Baseline explanation branch -> baseline")

    assert "render_sub_rank_card" not in app_text
    assert app_text.count("generate_active_explanation(") >= 2
    print("[PASS] 4 Active explanation views use one selector; obsolete card path absent")

    assert OFFICIAL_COMPETITION in app_text and "데이터톤" not in app_text
    print("[PASS] 5 Footer official competition name; stale datathon 0")

    comparison_label = "⚖️ 통합 대중교통 모델 vs 도시철도 중심 개선 모델"
    assert comparison_label in app_text and "⚖️ Baseline vs 통합교통 모델" not in app_text
    assert 'candidate="baseline"' in app_text and "is_improved=True" in app_text
    print("[PASS] 6 Comparison label matches actual improved-vs-integrated branches")

    ranking_text = (ROOT / "src/recommendation/ranking.py").read_text(encoding="utf-8")
    assert assigned_literal(ast.parse(ranking_text), "sort_cols") == SORT_KEYS
    assert "[total_score, demand_score, target_fit_score, pop_total]" in reproducibility
    print("[PASS] 7 Ranking documentation matches production sort keys")

    industries = assigned_literal(tree, "ind_options")
    targets = assigned_literal(tree, "target_options")
    demo_count = assigned_dict_length(tree, "DEMO_SCENARIOS")
    assert len(targets) == 5 and "5개 타깃" in readme
    print("[PASS] 8 README target count matches 5 UI options")
    assert len(industries) == 8 and industries[-1] == "직접 입력" and "7개 대표 업종" in readme and "직접 입력" in readme
    print("[PASS] 9 README industry inventory matches 7 presets + direct input")
    assert "10대 이하 (0~19세)" in targets and "`10대 이하 (0~19세)`" in judge
    print("[PASS] 10 README_JUDGE target label resolves in UI and feature range")

    for text in (app_text, readme, judge, reproducibility, model_card, json.dumps(manifest, ensure_ascii=False)):
        assert TEAM in text
    print("[PASS] 11 Team name consistent across code/docs/manifest")

    assert assigned_list_length(tree, "model_options") == 3
    assert "도시철도 중심 개선 모델" in model_card and "통합 대중교통 모델" in model_card
    print("[PASS] 12 Three model concepts and comparison names are consistent")

    assert len(WEIGHT_PRESETS) == 6 and demo_count == 7
    for label in ("기본 균형형", "타깃 고객 집중형 (트렌디/특화 소비)", comparison_label):
        assert label in app_text and label in judge
    assert 'hasattr(st, "iframe")' in app_text and "components.html(map_html" in app_text
    print("[PASS] 13 Judge-facing preset/tab labels resolve in production UI")

    dong, store = load_inputs()
    generators = {
        "Baseline": generate_explanation,
        "Improved": generate_improved_explanation,
        "Integrated": generate_enhanced_explanation,
    }
    scenarios = (
        ("카페", "2030", "기본 균형형"),
        ("한식", "전체", "배후 수요 집중형 (대형 매장/안정형)"),
        ("미용실", "2030", "기본 균형형"),
        ("학원", "10대", "타깃 고객 집중형 (트렌디/특화 소비)"),
        ("종합소매", "전체", "기본 균형형"),
        ("숙박", "2030", "기본 균형형"),
    )
    for industry, target, preset in scenarios:
        models, meta = score_three_models(dong, store, industry, target, WEIGHT_PRESETS[preset])
        for name, frame in models.items():
            assert not frame.duplicated(SORT_KEYS, keep=False).any(), (industry, target, name, "duplicate sort key")
            for _, row in frame.head(5).iterrows():
                exp = generators[name](row, meta)
                assert exp["summary_sentence"] and isinstance(exp["strengths"], list) and isinstance(exp["cautions"], list)
    print("[PASS] 14 18 model-scenarios have unique sort keys; 90 Top5 explanations smoke")

    print("=" * 72)
    print("PHASE 19: 14/14 PASS")
    print("=" * 72)


if __name__ == "__main__":
    main()
