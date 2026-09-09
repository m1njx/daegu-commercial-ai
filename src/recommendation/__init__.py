# -*- coding: utf-8 -*-
"""
src/recommendation

대구 AI 상권·창업 입지 추천 서비스 - 추천 엔진 패키지
"""

from .feature_builder import build_dong_industry_features
from .scoring import calculate_component_scores, compute_total_score, BASELINE_WEIGHTS
from .ranking import rank_locations
from .explain import generate_explanation
from .sensitivity import run_sensitivity_analysis, run_ablation_test

__all__ = [
    "build_dong_industry_features",
    "calculate_component_scores",
    "compute_total_score",
    "BASELINE_WEIGHTS",
    "rank_locations",
    "generate_explanation",
    "run_sensitivity_analysis",
    "run_ablation_test",
]
