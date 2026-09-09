# -*- coding: utf-8 -*-
"""
src/recommendation/personalization.py

사용자 맞춤형 가중치 조정 및 개인화 추천 모듈
- 6대 컴포넌트(Demand, Target Fit, Competition, Accessibility, Parking, Industry Fit) 가중치 정규화
- 비음수(Non-negative) 보장 및 합계 100%(1.0) 자동 정규화
- 사용자 사전 프리셋 시나리오 지원
- 유효성 검증 및 기본값 복원 기능
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

# Phase 5 Baseline 가중치 상수
BASELINE_WEIGHTS: Dict[str, float] = {
    "demand": 0.30,
    "target_fit": 0.20,
    "competition": 0.15,
    "accessibility": 0.15,
    "parking": 0.10,
    "industry_fit": 0.10,
}

# 한국어 컴포넌트 명칭 매핑
COMPONENT_NAMES: Dict[str, str] = {
    "demand": "배후 수요",
    "target_fit": "타깃 적합도",
    "competition": "경쟁 기회도",
    "accessibility": "교통 접근성",
    "parking": "주차 공급",
    "industry_fit": "업종 특화도",
}

# 사용자 추천 프리셋 시나리오
WEIGHT_PRESETS: Dict[str, Dict[str, float]] = {
    "기본 균형형": {
        "demand": 0.30,
        "target_fit": 0.20,
        "competition": 0.15,
        "accessibility": 0.15,
        "parking": 0.10,
        "industry_fit": 0.10,
    },
    "배후 수요 집중형 (대형 매장/안정형)": {
        "demand": 0.45,
        "target_fit": 0.15,
        "competition": 0.10,
        "accessibility": 0.15,
        "parking": 0.10,
        "industry_fit": 0.05,
    },
    "타깃 고객 집중형 (트렌디/특화 소비)": {
        "demand": 0.15,
        "target_fit": 0.45,
        "competition": 0.10,
        "accessibility": 0.15,
        "parking": 0.05,
        "industry_fit": 0.10,
    },
    "대중교통 접근성 우선형 (도보 테이크아웃)": {
        "demand": 0.20,
        "target_fit": 0.15,
        "competition": 0.10,
        "accessibility": 0.35,
        "parking": 0.10,
        "industry_fit": 0.10,
    },
    "경쟁 회피 (블루오션 개척형)": {
        "demand": 0.20,
        "target_fit": 0.15,
        "competition": 0.40,
        "accessibility": 0.10,
        "parking": 0.05,
        "industry_fit": 0.10,
    },
    "주차/차량 방문 중심형 (외곽/대형 식당)": {
        "demand": 0.20,
        "target_fit": 0.10,
        "competition": 0.10,
        "accessibility": 0.10,
        "parking": 0.40,
        "industry_fit": 0.10,
    },
}

def validate_and_normalize_weights(
    weights: Optional[Dict[str, float]] = None
) -> Dict[str, float]:
    """
    사용자가 입력한 가중치 딕셔너리를 검증하고 총합이 1.0(100%)이 되도록 정규화합니다.
    - 음수값은 0.0으로 클리핑
    - 전체 합계가 0 이하이거나 None인 경우 BASELINE_WEIGHTS로 복원
    - 각 가중치의 소수점 4자리 반올림 정규화
    """
    if weights is None:
        return dict(BASELINE_WEIGHTS)
    
    normalized = {}
    for k in BASELINE_WEIGHTS.keys():
        val = weights.get(k, 0.0)
        # float 변환 및 음수 방지
        try:
            val_float = float(val)
        except (ValueError, TypeError):
            val_float = 0.0
        # NaN/Inf otherwise survive max() and poison every downstream score.
        normalized[k] = max(0.0, val_float) if np.isfinite(val_float) else 0.0
        
    total = sum(normalized.values())
    if total <= 0.0:
        # 모든 가중치가 0인 비정상 입력 시 Baseline으로 복원
        return dict(BASELINE_WEIGHTS)
        
    result = {k: round(v / total, 4) for k, v in normalized.items()}
    # Four-decimal rounding can otherwise produce totals such as 1.0002.
    # Put the tiny residual on the largest component to preserve an exact simplex.
    residual = round(1.0 - sum(result.values()), 4)
    if residual:
        largest_key = max(result, key=result.get)
        result[largest_key] = round(result[largest_key] + residual, 4)
    return result

def is_baseline_weights(weights: Dict[str, float], tolerance: float = 1e-3) -> bool:
    """
    주어진 가중치가 BASELINE_WEIGHTS와 동일한지 확인합니다.
    """
    norm_w = validate_and_normalize_weights(weights)
    for k, v in BASELINE_WEIGHTS.items():
        if abs(norm_w.get(k, 0.0) - v) > tolerance:
            return False
    return True

def format_weights_summary(weights: Dict[str, float]) -> str:
    """
    가중치를 % 형식의 읽기 쉬운 문자열로 반환합니다.
    """
    norm = validate_and_normalize_weights(weights)
    parts = [f"{COMPONENT_NAMES.get(k, k)} {norm[k]*100:.1f}%" for k in BASELINE_WEIGHTS.keys()]
    return ", ".join(parts)
