# -*- coding: utf-8 -*-
"""
app/app.py

대구 소상공인 AI 상권·창업 입지 추천 서비스 (Warm Pastel Dashboard)
- 6대 컴포넌트 점수 상태 통일 색상 체계 (🟢 추천 70~100 / 🟡 보통 40~69.99 / 🔴 비추천 0~39.99)
- 따뜻하고 친근한 파스텔톤의 프리미엄 데이터 대시보드 (핀테크 / 공공 금융 컨설팅 감성)
- 실제 대구시 공공데이터(11.8만 점포, 235만 인구, 94역 도시철도, 24.7만면 부설주차장) 기반
- Phase 5 BASELINE 기준선 모델 및 Phase 6 IMPROVED(0점포 상권 왜곡 보정) 모델 지원
- 사용자 맞춤형 6대 가중치 100% 정규화(Simplex Normalization) 및 원클릭 데모 시나리오 제공
- 행정동 단위 Folium Choropleth 지도, 94개 도시철도역 오버레이 및 iM뱅크 금융 연계 로드맵
"""

import sys
import os
import re
import html
import base64
from pathlib import Path
import json
import textwrap
import logging
import numpy as np
import pandas as pd
import geopandas as gpd
import folium
import streamlit as st
import streamlit.components.v1 as components
from scipy.stats import spearmanr

# 프로젝트 루트 경로 설정
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.recommendation.feature_builder import build_dong_industry_features
from src.recommendation.scoring import calculate_component_scores, compute_total_score, BASELINE_WEIGHTS
from src.recommendation.ranking import rank_locations
from src.recommendation.explain import generate_explanation
from src.recommendation.improved import calculate_improved_scores, generate_improved_explanation
from src.recommendation.transit_enhanced import (
    calculate_enhanced_scores,
    calculate_enhanced_transit_accessibility,
    calculate_bus_accessibility_score,
    generate_enhanced_explanation,
    TRANSIT_CANDIDATES,
)
from src.recommendation.personalization import (
    validate_and_normalize_weights,
    WEIGHT_PRESETS,
    COMPONENT_NAMES,
    format_weights_summary,
)

logger = logging.getLogger(__name__)

# ----------------------------------------------------
# 0. 페이지 기본 설정 및 상태 기반 파스텔 CSS 테마
# ----------------------------------------------------
st.set_page_config(
    page_title="대구 소상공인 AI 상권·창업 입지 추천 서비스",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

def clean_markdown_to_html(text: str) -> str:
    """Convert supported inline Markdown to safe HTML without leaking syntax."""
    if not text:
        return ""
    cleaned = html.escape(str(text), quote=True)
    # Keep link labels but never inject an untrusted URL into application HTML.
    cleaned = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", cleaned)
    cleaned = re.sub(r"`([^`]+)`", r"<code>\1</code>", cleaned)
    cleaned = re.sub(r"\*\*(.+?)\*\*|__(.+?)__", lambda m: f"<b>{m.group(1) or m.group(2)}</b>", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"~~(.+?)~~", r"<s>\1</s>", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)|(?<!_)_([^_]+?)_(?!_)", lambda m: f"<i>{m.group(1) or m.group(2)}</i>", cleaned, flags=re.DOTALL)
    # Malformed/unclosed formatting must be shown as plain text, not raw syntax.
    cleaned = cleaned.replace("**", "").replace("__", "").replace("~~", "").replace("`", "")
    return cleaned

def render_html(html_str: str):
    """Render application-owned HTML templates.

    Values originating in datasets must be passed through
    ``clean_markdown_to_html`` before interpolation.
    """
    st.html(textwrap.dedent(html_str).strip())

def get_score_status(score: float):
    """
    6대 컴포넌트 점수 상태 통일 분류 (0~100 수치 기준):
    - 70 ~ 100: 🟢 추천 (우수 상권 지표)
    - 40 ~ 69.99: 🟡 보통 (평균 수준 지표)
    - 0 ~ 39.99: 🔴 비추천 (확인 필요 취약 지표)
    """
    sc = float(score)
    if sc >= 70.0:
        return {
            "label": "추천",
            "emoji": "🟢",
            "full_badge": "🟢 추천",
            "bg": "#ECFDF3",
            "border": "#86EFAC",
            "text": "#15803D",
            "accent": "#22C55E",
            "grade": "recommended",
        }
    elif sc >= 40.0:
        return {
            "label": "보통",
            "emoji": "🟡",
            "full_badge": "🟡 보통",
            "bg": "#FFFBEB",
            "border": "#FDE68A",
            "text": "#A16207",
            "accent": "#EAB308",
            "grade": "normal",
        }
    else:
        return {
            "label": "비추천",
            "emoji": "🔴",
            "full_badge": "🔴 비추천",
            "bg": "#FEF2F2",
            "border": "#FCA5A5",
            "text": "#B91C1C",
            "accent": "#EF4444",
            "grade": "caution",
        }

def describe_rank_similarity(rho: float) -> str:
    """Describe the observed rank correlation without overstating stability."""
    if rho >= 0.985:
        return "높은 순위 유사도"
    if rho >= 0.95:
        return "대체로 유사하나 일부 순위 변화"
    return "순위 변화 확인 필요"

# 스타일 주입
render_html("""
<style>
    html, body, [class*="css"] {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif !important;
    }

    .stApp {
        background-color: #F8FAFC !important;
        color: #1E293B !important;
    }
    
    .main .block-container {
        max-width: 1220px !important;
        padding-top: 1.8rem !important;
        padding-bottom: 3.5rem !important;
        padding-left: 1.8rem !important;
        padding-right: 1.8rem !important;
        margin: 0 auto !important;
    }

    [data-testid="stSidebar"] {
        min-width: 280px !important;
        max-width: 310px !important;
        background-color: #FFFFFF !important;
        border-right: 1px solid #E2E8F0 !important;
        box-shadow: 2px 0 10px rgba(0, 0, 0, 0.02) !important;
    }

    [data-testid="stSidebar"] > div:first-child {
        background-color: #FFFFFF !important;
        padding: 1.25rem 1rem 2rem 1rem !important;
    }

    [data-testid="stSidebar"] label, .stApp label {
        color: #334155 !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
    }

    div[data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
        border-color: #CBD5E1 !important;
        color: #0F172A !important;
        border-radius: 10px !important;
    }

    div[data-baseweb="select"] span {
        color: #0F172A !important;
        font-weight: 500 !important;
    }

    [data-testid="stSidebar"] button {
        width: 100% !important;
        white-space: nowrap !important;
        word-break: keep-all !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }

    [data-testid="stSidebar"] button p,
    [data-testid="stSidebar"] button div,
    [data-testid="stSidebar"] button span {
        white-space: nowrap !important;
        word-break: keep-all !important;
        text-overflow: clip !important;
        display: inline-block !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    button[kind="primary"] {
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.55rem 0.8rem !important;
        font-weight: 700 !important;
        font-size: 0.92rem !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2) !important;
        width: 100% !important;
        margin-bottom: 6px !important;
        white-space: nowrap !important;
        word-break: keep-all !important;
    }
    button[kind="primary"]:hover {
        box-shadow: 0 6px 16px rgba(37, 99, 235, 0.3) !important;
        transform: translateY(-1px) !important;
    }

    button[kind="secondary"] {
        background-color: #F8FAFC !important;
        color: #64748B !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 10px !important;
        padding: 0.45rem 0.8rem !important;
        font-weight: 600 !important;
        font-size: 0.84rem !important;
        width: 100% !important;
        white-space: nowrap !important;
        word-break: keep-all !important;
    }
    button[kind="secondary"]:hover {
        background-color: #F1F5F9 !important;
        color: #334155 !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px !important;
        border-bottom: 2px solid #E2E8F0 !important;
        padding-bottom: 4px !important;
        margin-bottom: 20px !important;
        background-color: transparent !important;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 9px 18px !important;
        font-weight: 600 !important;
        font-size: 0.92rem !important;
        color: #64748B !important;
        border-radius: 10px !important;
        background-color: #F1F5F9 !important;
        border: 1px solid transparent !important;
    }
    .stTabs [aria-selected="true"] {
        color: #1E40AF !important;
        background-color: #DBEAFE !important;
        border-color: #BFDBFE !important;
        font-weight: 700 !important;
    }

    .hero-header-title {
        font-size: 2.1rem;
        font-weight: 800;
        color: #0F172A;
        letter-spacing: -0.03em;
        margin-bottom: 6px;
    }
    .hero-header-sub {
        font-size: 1.02rem;
        color: #475569;
        font-weight: 400;
        line-height: 1.6;
        margin-bottom: 14px;
    }

    .info-card-blue {
        background: linear-gradient(135deg, #F0F7FF 0%, #EBF4FF 100%);
        border: 1px solid #BAE6FD;
        border-left: 5px solid #3B82F6;
        border-radius: 14px;
        padding: 13px 18px;
        margin-bottom: 16px;
        box-shadow: 0 2px 8px rgba(59, 130, 246, 0.04);
    }
    .info-card-title {
        font-size: 1.0rem;
        font-weight: 700;
        color: #1E40AF;
        margin-bottom: 3px;
    }
    .info-card-content {
        font-size: 0.9rem;
        color: #1E293B;
        line-height: 1.5;
    }
    .info-card-notice {
        font-size: 0.78rem;
        color: #64748B;
        margin-top: 5px;
        border-top: 1px dashed #CBD5E1;
        padding-top: 4px;
    }

    .kpi-container {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 12px;
        margin-bottom: 20px;
    }
    .kpi-card {
        background-color: #FFFFFF;
        border-radius: 14px;
        padding: 14px 16px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.02);
    }
    .kpi-blue   { background-color: #F8FAFF; border-top: 4px solid #3B82F6; }
    .kpi-green  { background-color: #F6FDF9; border-top: 4px solid #10B981; }
    .kpi-purple { background-color: #FAF7FF; border-top: 4px solid #A855F7; }
    .kpi-sky    { background-color: #F4FAFF; border-top: 4px solid #0EA5E9; }
    .kpi-orange { background-color: #FFFAF5; border-top: 4px solid #F97316; }

    .kpi-label { font-size: 0.8rem; font-weight: 600; color: #64748B; margin-bottom: 2px; }
    .kpi-val   { font-size: 1.35rem; font-weight: 800; color: #0F172A; }
    .kpi-sub   { font-size: 0.75rem; color: #94A3B8; margin-top: 2px; }

    .top1-hero-card {
        background: linear-gradient(135deg, #FEFDF5 0%, #FEFCE8 100%);
        border: 1.5px solid #FDE68A;
        border-radius: 18px;
        padding: 22px 24px;
        box-shadow: 0 6px 20px rgba(245, 158, 11, 0.08);
        margin-bottom: 16px;
    }
    .top1-header-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
    }
    .top1-badge-gold {
        background-color: #FEF3C7;
        color: #92400E;
        font-size: 0.95rem;
        font-weight: 800;
        padding: 4px 12px;
        border-radius: 16px;
        border: 1px solid #FCD34D;
    }
    .top1-score-tag {
        font-size: 1.55rem;
        font-weight: 800;
        color: #B45309;
    }

    .sub-rank-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 14px 18px;
        margin-bottom: 10px;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.02);
    }

    .badge-market-validated {
        background-color: #ECFDF5;
        color: #065F46;
        font-size: 0.78rem;
        font-weight: 700;
        padding: 3px 10px;
        border-radius: 16px;
        border: 1px solid #A7F3D0;
    }
    .badge-market-unentered {
        background-color: #FFFBEB;
        color: #92400E;
        font-size: 0.78rem;
        font-weight: 700;
        padding: 3px 10px;
        border-radius: 16px;
        border: 1px solid #FDE68A;
    }

    .step-card {
        background-color: #FFFFFF;
        border-radius: 14px;
        padding: 16px 18px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.02);
        height: 100%;
    }
    .step-badge-active {
        background-color: #ECFDF5;
        color: #065F46;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 700;
    }
    .step-badge-future {
        background-color: #F1F5F9;
        color: #475569;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 700;
    }
</style>
""")

hero_asset_path = ROOT_DIR / "app/assets/daegu_dashboard_hero.png"
if hero_asset_path.exists():
    hero_asset_b64 = base64.b64encode(hero_asset_path.read_bytes()).decode("ascii")
    render_html(f"""
    <style>
        .hero-banner {{
            background-image:
                linear-gradient(90deg, rgba(255,255,255,.98) 0%, rgba(255,255,255,.91) 35%, rgba(255,255,255,.18) 67%, rgba(255,255,255,.04) 100%),
                url('data:image/png;base64,{hero_asset_b64}') !important;
            background-size: cover !important;
            background-position: center 53% !important;
        }}
    </style>
    """)

logo_asset_path = ROOT_DIR / "app/assets/im_bank_logo.png"
logo_data_uri = ""
if logo_asset_path.exists():
    logo_asset_b64 = base64.b64encode(logo_asset_path.read_bytes()).decode("ascii")
    logo_data_uri = f"data:image/png;base64,{logo_asset_b64}"

# Reference-dashboard visual system: layout-only overrides.
render_html("""
<style>
    :root {
        --navy: #173869;
        --blue: #4F73F1;
        --line: #DDE7F2;
        --canvas: #F5F9FD;
        --muted: #6B7F99;
    }
    header[data-testid="stHeader"] { background: transparent !important; height: 0 !important; overflow:visible !important; }
    #MainMenu, footer, [data-testid="stToolbar"] { visibility: hidden !important; }
    [data-testid="stSidebarCollapseButton"] {
        display:flex !important; visibility:visible !important; opacity:1 !important;
        position:absolute !important; top:10px !important; right:10px !important; z-index:100001 !important;
    }
    [data-testid="stSidebarCollapseButton"] button {
        display:flex !important; visibility:visible !important; opacity:1 !important;
        width:34px !important; height:34px !important; min-height:34px !important;
        color:#315273 !important; background:#FFFFFF !important; border:1px solid #D8E3EF !important;
        border-radius:9px !important; box-shadow:0 3px 10px rgba(30,65,104,.10) !important;
    }
    .stApp { background: var(--canvas) !important; }
    .main .block-container {
        max-width: 1540px !important;
        padding: 18px 22px 28px !important;
    }
    [data-testid="stMainBlockContainer"] {
        width:100% !important;
        max-width:1540px !important;
        box-sizing:border-box !important;
        transition:max-width .2s ease, width .2s ease !important;
    }
    [data-testid="stSidebar"] {
        min-width: 282px !important;
        max-width: 282px !important;
        background: #F9FBFE !important;
        border-right: 1px solid #E1EAF4 !important;
        box-shadow: 6px 0 24px rgba(27, 55, 91, .045) !important;
    }
    [data-testid="stSidebar"][aria-expanded="false"] {
        min-width:0 !important; max-width:0 !important; width:0 !important;
        transform:none !important; border:0 !important; box-shadow:none !important;
        overflow:visible !important;
    }
    [data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarUserContent"] {
        display:none !important;
    }
    [data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarCollapseButton"] {
        position:fixed !important; left:10px !important; right:auto !important; top:10px !important;
    }
    [data-testid="stMain"] { flex:1 1 auto !important; min-width:0 !important; }
    [data-testid="stSidebar"] > div:first-child { padding: 24px 18px !important; }
    [data-testid="stSidebar"] h3 { color: var(--navy) !important; font-size: 1.05rem !important; }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #71839A; }
    [data-testid="stSidebar"] div[data-baseweb="select"] > div,
    [data-testid="stSidebar"] .stTextInput input {
        min-height: 43px !important; border-radius: 9px !important; border-color: #D8E2EE !important;
        box-shadow: 0 2px 7px rgba(25, 57, 96, .04) !important;
    }
    [data-testid="stSidebar"] [data-testid="stSlider"] { padding: 0 2px 5px !important; }
    [data-testid="stSidebar"] hr { margin: 14px 0 !important; border-color: #E6EDF5 !important; }
    button[kind="primary"] {
        min-height: 48px !important; border-radius: 8px !important;
        background: linear-gradient(110deg, #4F7BF4, #6A62F3) !important;
        box-shadow: 0 7px 18px rgba(79, 115, 241, .22) !important;
    }
    .hero-banner {
        position: relative; overflow: hidden; min-height: 120px; padding: 24px 30px;
        border: 1px solid #DCEAF4; border-radius: 13px 13px 0 0;
        background:
          radial-gradient(circle at 78% 17%, rgba(255,255,255,.95) 0 3%, transparent 3.2%),
          linear-gradient(145deg, transparent 63%, rgba(82,194,169,.18) 63% 70%, transparent 70%),
          linear-gradient(160deg, transparent 72%, rgba(70,155,214,.17) 72% 80%, transparent 80%),
          linear-gradient(110deg, #FFFFFF 0%, #F7FCFF 48%, #EAF9FB 100%);
        box-shadow: 0 3px 14px rgba(38, 72, 108, .05);
    }
    .hero-brand { display:flex; align-items:center; gap:14px; }
    .hero-symbol { font-size:2.15rem; filter: drop-shadow(0 3px 4px rgba(49,110,183,.15)); }
    .hero-header-title { font-size: 1.72rem; color: var(--navy); margin:0; line-height:1.25; }
    .hero-header-sub { font-size: .88rem; color:#627891; margin:7px 0 0 52px; line-height:1.55; }
    .hero-slogan { position:absolute; right:160px; top:29px; color:#438DB3; font-weight:700; font-size:.95rem; transform:rotate(-3deg); text-align:center; line-height:1.6; }
    .hero-bank { position:absolute; right:28px; top:26px; color:#263E64; font-size:1.25rem; font-weight:850; }
    .hero-bank em { color:#16A7A5; font-style:normal; font-size:1.55rem; }
    .hero-bank img {
        display:block;
        width:118px;
        height:auto;
        object-fit:contain;
        /* The supplied official PNG has an opaque white matte despite being
           RGBA. Multiply removes that matte against the illustrated banner
           while preserving the exact brand artwork and antialiased edges. */
        mix-blend-mode:multiply;
    }
    .overview-row { display:grid; grid-template-columns:2.35fr repeat(5,1fr); gap:10px; margin:10px 0 14px; }
    .info-card-blue, .kpi-card { margin:0; min-height:82px; border-radius:10px; box-sizing:border-box; box-shadow:0 3px 10px rgba(31,61,96,.035); }
    .info-card-blue { padding:13px 16px; border-left:1px solid #BFE1F1; }
    .info-card-title { font-size:.92rem; }
    .info-card-content { font-size:.76rem; line-height:1.45; }
    .info-card-notice { display:none; }
    .kpi-card { padding:13px 12px; text-align:center; border-top-width:1px; }
    .kpi-label { font-size:.72rem; }
    .kpi-val { font-size:1.03rem; color:#173869; margin-top:5px; }
    .kpi-sub { display:none; }
    .stTabs [data-baseweb="tab-list"] {
        gap:0 !important; padding:0 8px !important; margin:0 0 14px !important; height:48px;
        background:#FFF !important; border:1px solid var(--line) !important; border-radius:10px !important;
        box-shadow:0 2px 8px rgba(31,61,96,.035);
    }
    .stTabs [data-baseweb="tab"] {
        flex:1; justify-content:center; height:47px; padding:8px 12px !important;
        border:0 !important; border-radius:0 !important; background:transparent !important;
        color:#566D88 !important; font-size:.82rem !important;
    }
    .stTabs [aria-selected="true"] { color:#416DE5 !important; box-shadow:inset 0 -3px #527AF1; }
    .stTabs [data-baseweb="tab-panel"] { padding-top:0 !important; }
    .top1-hero-card, .sub-rank-card, .step-card {
        border-radius:10px; box-shadow:0 3px 12px rgba(31,61,96,.045);
    }
    .top1-hero-card { padding:16px 18px; }
    .sub-rank-card { padding:12px 14px; }
    iframe { border-radius:10px !important; }
    .dashboard-panel { background:#FFF; border:1px solid var(--line); border-radius:11px; padding:14px; box-shadow:0 3px 12px rgba(31,61,96,.045); }
    .panel-head { display:flex; align-items:center; justify-content:space-between; margin-bottom:12px; color:#173869; font-size:1rem; font-weight:800; }
    .panel-chip { font-size:.7rem; color:#44617F; background:#F2F7FC; border-radius:14px; padding:5px 9px; }
    .compact-top-grid { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:8px; }
    .compact-rank-card { min-height:245px; border:1px solid #DFE7F1; border-radius:9px; padding:11px 10px; background:linear-gradient(180deg,#FFF,#FBFDFF); }
    .compact-rank-card.first { background:linear-gradient(180deg,#FFFDF3,#FFFBEA); border-color:#F5D66D; box-shadow:0 3px 10px rgba(225,171,31,.10); }
    .compact-rank-link { display:block; color:inherit !important; text-decoration:none !important; border-radius:9px; transition:transform .16s ease, box-shadow .16s ease; }
    .compact-rank-link:hover { transform:translateY(-2px); box-shadow:0 7px 16px rgba(38,79,124,.12); }
    .compact-rank-card.selected { border:2px solid #587CF2; box-shadow:0 0 0 3px rgba(88,124,242,.10); }
    .rank-ball { width:27px; height:27px; display:inline-flex; align-items:center; justify-content:center; border-radius:50%; background:#E8F0FA; color:#345374; font-size:.75rem; font-weight:800; }
    .first .rank-ball { background:#F6CA47; color:#76520A; }
    .compact-name { margin-top:9px; color:#233D60; font-size:.87rem; font-weight:800; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
    .compact-score-label { color:#8494A7; font-size:.65rem; margin-top:12px; }
    .compact-score { color:#2859B8; font-size:1.2rem; font-weight:850; margin-top:2px; }
    .compact-grade { display:block; text-align:center; margin:9px 0; padding:4px; border-radius:12px; background:#EEF9F5; color:#16836A; font-size:.68rem; font-weight:750; }
    .compact-reason-title { color:#435B76; font-size:.68rem; font-weight:800; margin:10px 0 5px; }
    .compact-reason { color:#637991; font-size:.63rem; line-height:1.65; }
    [data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:10px; overflow:hidden; }
    @media (max-width: 1100px) {
        .overview-row { grid-template-columns:repeat(2,1fr); }
        .overview-row .info-card-blue { grid-column:1/-1; }
        .hero-slogan { display:none; }
    }
</style>
""")

# ----------------------------------------------------
# 1. 데이터 로딩 (캐싱)
# ----------------------------------------------------
MODEL_MODE_INTEGRATED = "통합 대중교통 모델 (권장 / 도시철도 70% + 시내버스 30%)"
MODEL_MODE_SUBWAY_IMPROVED = "도시철도 중심 모델 (도시철도 역세권 중심)"
MODEL_MODE_BASELINE = "초기 기준선 모델 (도시철도 단순 거리)"

@st.cache_data
def load_data():
    dong_path = ROOT_DIR / "data/processed/feature_mart/commercial_feature_mart_dong.parquet"
    store_path = ROOT_DIR / "data/processed/feature_mart/store_spatial_features.parquet"
    geojson_path = ROOT_DIR / "data/processed/geojson/대구_행정동_경계_20230701.geojson"
    subway_path = ROOT_DIR / "data/processed/transit/대구도시철도_역별_위경도좌표.csv"
    bus_path = ROOT_DIR / "data/processed/transit/bus/daegu_bus_dong_features.parquet"
    
    df_dong = pd.read_parquet(dong_path)
    df_store = pd.read_parquet(store_path)
    gdf_dong = gpd.read_file(geojson_path)
    
    df_subway = None
    if subway_path.exists():
        df_subway = pd.read_csv(subway_path)
        
    df_bus_dong = None
    if bus_path.exists():
        df_bus_dong = pd.read_parquet(bus_path)
        bus_cols = [
            "adm_cd2", "dong_bus_stop_count", "dong_daily_bus_boarding",
            "dong_daily_bus_alighting", "dong_daily_bus_total",
            "dong_bus_stop_density", "dong_bus_ridership_per_stop",
            "avg_dist_to_bus_m", "ratio_stores_in_bus_300m"
        ]
        merge_cols = [c for c in bus_cols if c == "adm_cd2" or c not in df_dong.columns]
        df_dong = df_dong.merge(df_bus_dong[merge_cols], on="adm_cd2", how="left")
        
    gdf_proj = gdf_dong.to_crs(epsg=5179)
    centroids = gdf_proj.geometry.centroid.to_crs(epsg=4326)
    gdf_dong["lat"] = centroids.y
    gdf_dong["lng"] = centroids.x
    
    if df_bus_dong is not None:
        gdf_dong = gdf_dong.merge(
            df_bus_dong[["adm_cd2", "dong_bus_stop_count", "dong_daily_bus_total"]],
            on="adm_cd2",
            how="left"
        )
        gdf_dong["dong_bus_stop_count"] = gdf_dong["dong_bus_stop_count"].fillna(0).astype(int)
        gdf_dong["dong_daily_bus_total"] = gdf_dong["dong_daily_bus_total"].fillna(0.0)
    
    return df_dong, df_store, gdf_dong, df_subway, df_bus_dong

try:
    df_dong, df_store, gdf_dong, df_subway, df_bus_dong = load_data()
except Exception:
    logger.exception("Application data loading failed")
    st.error("필수 분석 데이터를 불러오지 못했습니다. 데이터 파일과 실행 환경을 확인해 주세요.")
    st.stop()

# ----------------------------------------------------
# 2. 6대 실전 창업 데모 시나리오 사전 정의
# ----------------------------------------------------
DEMO_SCENARIOS = {
    "직접 조건 설정 (Custom)": None,
    "시나리오 1: ☕ 카페 + 2030 청년층 (신암4동 1위 - 동대구역세권/청년 집적)": {
        "industry": "카페",
        "target_label": "2030 청년 소비층 (20~39세)",
        "preset": "기본 균형형",
        "mode": MODEL_MODE_INTEGRATED,
    },
    "시나리오 2: 🍚 한식 음식점 + 전체 인구 (상인1동 1위 - 역세권·버스 환승/상권 집적)": {
        "industry": "한식",
        "target_label": "전체 인구 (전연령)",
        "preset": "배후 수요 집중형 (대형 매장/안정형)",
        "mode": MODEL_MODE_INTEGRATED,
    },
    "시나리오 3: 💇 미용실 + 2030 청년층 (칠성동 1위 - 침산·칠성 주거·상업 복합 상권)": {
        "industry": "미용실",
        "target_label": "2030 청년 소비층 (20~39세)",
        "preset": "기본 균형형",
        "mode": MODEL_MODE_INTEGRATED,
    },
    "시나리오 4: 📚 학원 + 10대 이하 (범어1동 1위 - 학원 특화도 LQ 1.90)": {
        "industry": "학원",
        "target_label": "10대 이하 (0~19세)",
        "preset": "타깃 고객 집중형 (트렌디/특화 소비)",
        "mode": MODEL_MODE_INTEGRATED,
    },
    "시나리오 5: 🛍️ 종합소매점 + 전체 인구 (상인1동 1위 - 월배로 중심상권/대중교통 접근)": {
        "industry": "종합소매",
        "target_label": "전체 인구 (전연령)",
        "preset": "기본 균형형",
        "mode": MODEL_MODE_INTEGRATED,
    },
    "시나리오 6: 🏨 숙박업 + 2030 청년층 (숙박업 후보지 및 점포 미확인 지역 보정 비교)": {
        "industry": "숙박",
        "target_label": "2030 청년 소비층 (20~39세)",
        "preset": "기본 균형형",
        "mode": MODEL_MODE_INTEGRATED,
    },
}

def apply_demo_scenario() -> None:
    """Apply every control belonging to the selected demo atomically."""
    config = DEMO_SCENARIOS.get(st.session_state.get("selected_demo"))
    if not config:
        return
    st.session_state.industry_choice = config["industry"]
    st.session_state.target_choice = config["target_label"]
    st.session_state.weight_preset = config["preset"]
    st.session_state.model_mode = config["mode"]
    st.session_state.discount_factor = 0.50
    st.session_state.filter_unentered = False
    st.session_state.user_weights = dict(WEIGHT_PRESETS[config["preset"]])
    st.session_state.last_preset = config["preset"]
    st.session_state.weight_widget_revision = st.session_state.get("weight_widget_revision", 0) + 1

# ----------------------------------------------------
# 3. Sidebar — 📍 창업 조건 입력 패널
# ----------------------------------------------------
st.sidebar.markdown("### 📍 창업 조건 입력")
st.sidebar.markdown(
    "<div style='font-size: 0.86rem; color: #475569; line-height: 1.5; margin-bottom: 12px;'>"
    "원하는 업종과 목표 고객을 설정하고<br>행정동별 상대적 입지 적합도를 비교해 보세요."
    "</div>",
    unsafe_allow_html=True
)

selected_demo = st.sidebar.selectbox(
    "🎬 심사위원 데모 시나리오",
    options=list(DEMO_SCENARIOS.keys()),
    index=0,
    help="공모전 심사용 6대 핵심 시나리오를 원클릭으로 불러옵니다.",
    key="selected_demo",
    on_change=apply_demo_scenario,
)
demo_cfg = DEMO_SCENARIOS[selected_demo]

ind_options = ["카페", "한식", "미용실", "학원", "종합소매", "숙박", "예술·스포츠", "직접 입력"]
def_ind_idx = 0
if demo_cfg:
    try:
        def_ind_idx = ind_options.index(demo_cfg["industry"])
    except ValueError:
        def_ind_idx = 0

industry_widget_args = {"key": "industry_choice"}
if "industry_choice" not in st.session_state:
    industry_widget_args["index"] = def_ind_idx
selected_ind_raw = st.sidebar.selectbox(
    "희망 업종 선택", ind_options, **industry_widget_args
)
if selected_ind_raw == "직접 입력":
    ind_query = st.sidebar.text_input(
        "업종 검색어 입력 (예: 일식, 중식)", value="중식", max_chars=50
    ).strip()
else:
    ind_query = selected_ind_raw

target_options = {
    "2030 청년 소비층 (20~39세)": "2030",
    "전체 인구 (전연령)": "전체",
    "10대 이하 (0~19세)": "10대",
    "4050 중장년 구매력층 (40~59세)": "4050",
    "60대 이상 시니어층": "60대",
}
target_keys = list(target_options.keys())
def_tgt_idx = 0
if demo_cfg:
    try:
        def_tgt_idx = target_keys.index(demo_cfg["target_label"])
    except ValueError:
        def_tgt_idx = 0

target_widget_args = {"key": "target_choice"}
if "target_choice" not in st.session_state:
    target_widget_args["index"] = def_tgt_idx
target_choice = st.sidebar.selectbox(
    "타깃 고객층 선택", options=target_keys, **target_widget_args
)
target_query = target_options[target_choice]

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚖️ 중요도 (개인화 가중치)")

preset_keys = list(WEIGHT_PRESETS.keys()) + ["사용자 직접 조정"]
def_preset_idx = 0
if demo_cfg:
    try:
        def_preset_idx = preset_keys.index(demo_cfg["preset"])
    except ValueError:
        def_preset_idx = 0

preset_widget_args = {"key": "weight_preset"}
if "weight_preset" not in st.session_state:
    preset_widget_args["index"] = def_preset_idx
preset_choice = st.sidebar.selectbox(
    "가중치 성향 프리셋",
    options=preset_keys,
    **preset_widget_args,
)

slider_info = [
    ("demand", "배후 수요", 30),
    ("target_fit", "타깃 적합도", 20),
    ("competition", "경쟁 기회도", 15),
    ("accessibility", "교통 접근성", 15),
    ("parking", "주차 공급", 10),
    ("industry_fit", "업종 특화도", 10),
]

if "weight_widget_revision" not in st.session_state:
    st.session_state.weight_widget_revision = 0

def reset_weight_controls() -> None:
    """Reset the preset and all slider widget state before the next rerun."""
    st.session_state.user_weights = dict(BASELINE_WEIGHTS)
    st.session_state.weight_preset = "기본 균형형"
    st.session_state.last_preset = "기본 균형형"
    st.session_state.weight_widget_revision += 1

if "user_weights" not in st.session_state or preset_choice != st.session_state.get("last_preset", ""):
    if preset_choice in WEIGHT_PRESETS:
        st.session_state.user_weights = dict(WEIGHT_PRESETS[preset_choice])
        # Use a fresh widget namespace so stale slider values cannot survive a
        # preset change in Streamlit's widget state.
        st.session_state.weight_widget_revision += 1
    st.session_state.last_preset = preset_choice

weights_raw = {}
for idx, (k, name, def_val) in enumerate(slider_info):
    curr_v = int(st.session_state.user_weights.get(k, def_val / 100.0) * 100)
    slider_key = f"sl_{k}_{st.session_state.weight_widget_revision}"
    v = st.sidebar.slider(f"{name}", min_value=0, max_value=100, value=curr_v, step=5, key=slider_key)
    weights_raw[k] = float(v)

norm_weights = validate_and_normalize_weights(weights_raw)

# 사이드바 가중치 정규화 합계 카드 (메인 화면 중복 노출 제거 및 사이드바 내 배치)
st.sidebar.html(textwrap.dedent(f"""
<div style='background-color: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 10px; padding: 10px 12px; margin: 8px 0 12px 0;'>
    <div style='font-size: 0.8rem; font-weight: 700; color: #15803D; margin-bottom: 3px;'>
        ✓ 현재 가중치 합계 100%
    </div>
    <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 3px; font-size: 0.75rem; color: #334155;'>
        <div>수요: <b>{norm_weights['demand']*100:.1f}%</b></div>
        <div>타깃: <b>{norm_weights['target_fit']*100:.1f}%</b></div>
        <div>경쟁: <b>{norm_weights['competition']*100:.1f}%</b></div>
        <div>교통: <b>{norm_weights['accessibility']*100:.1f}%</b></div>
        <div>주차: <b>{norm_weights['parking']*100:.1f}%</b></div>
        <div>특화: <b>{norm_weights['industry_fit']*100:.1f}%</b></div>
    </div>
</div>
""").strip())

if st.sidebar.button("✨ AI 입지 분석 실행", type="primary", width="stretch"):
    st.rerun()

st.sidebar.button(
    "가중치 초기화",
    type="secondary",
    width="stretch",
    on_click=reset_weight_controls,
)

with st.sidebar.expander("⚙️ 모델 버전 및 대중교통 설정 (고급)"):
    model_options = [
        MODEL_MODE_INTEGRATED,
        MODEL_MODE_SUBWAY_IMPROVED,
        MODEL_MODE_BASELINE,
    ]
    default_mode_idx = 0
    if demo_cfg and demo_cfg.get("mode") in model_options:
        default_mode_idx = model_options.index(demo_cfg["mode"])
    elif "model_mode" in st.session_state and st.session_state["model_mode"] in model_options:
        default_mode_idx = model_options.index(st.session_state["model_mode"])
        
    model_widget_args = {"key": "model_mode"}
    if "model_mode" not in st.session_state:
        model_widget_args["index"] = default_mode_idx
    model_mode = st.radio(
        "추천 모델 버전",
        options=model_options,
        **model_widget_args,
        help="권장: 도시철도(70%)와 시내버스(30%)를 결합한 통합 대중교통 모델입니다. 기존 도시철도 단독 모델과 비교할 수 있습니다."
    )
    is_integrated_mode = (model_mode == MODEL_MODE_INTEGRATED)
    is_improved_mode = (model_mode != MODEL_MODE_BASELINE)
    discount_widget_args = {"key": "discount_factor"}
    if "discount_factor" not in st.session_state:
        discount_widget_args["value"] = 0.50
    discount_factor_val = st.slider(
        "해당 업종 점포 미확인 지역 할인 계수 (α)", 0.0, 1.0, step=0.1, **discount_widget_args
    )
    exclude_widget_args = {"key": "filter_unentered"}
    if "filter_unentered" not in st.session_state:
        exclude_widget_args["value"] = False
    filter_unentered_val = st.checkbox(
        "해당 업종 점포 미확인 지역 완전 제외", **exclude_widget_args
    )

# ----------------------------------------------------
# 4. 실시간 추천 모델 계산 파이프라인
# ----------------------------------------------------
try:
    feat_df, meta = build_dong_industry_features(ind_query, target_query, df_dong, df_store)
except ValueError as e:
    st.error(f"입력한 업종을 처리할 수 없습니다: {e}")
    st.stop()
except Exception:
    logger.exception("Feature generation failed")
    st.error("추천 데이터를 계산하는 중 오류가 발생했습니다. 입력값을 확인한 뒤 다시 시도해 주세요.")
    st.stop()

# 버스 피처를 feat_df에 안전하게 결합
bus_feature_cols = [
    "dong_bus_stop_count", "dong_daily_bus_boarding", "dong_daily_bus_alighting",
    "dong_daily_bus_total", "dong_bus_stop_density", "dong_bus_ridership_per_stop",
    "avg_dist_to_bus_m", "ratio_stores_in_bus_300m"
]
for col in bus_feature_cols:
    if col in df_dong.columns:
        feat_df[col] = df_dong[col].values

# 1. 도시철도 중심 개선 모델 (도시철도 단독 + 0점포 보정)
base_scored = calculate_enhanced_scores(
    feat_df.copy(),
    weights=norm_weights,
    candidate="baseline",
    is_improved=True,
    min_stores=1,
    discount_factor=discount_factor_val,
)
base_ranked = rank_locations(base_scored)

# 2. Phase 8 Candidate B (대중교통 통합 모델: 도시철도 70% + 시내버스 30%)
cand_b_scored = calculate_enhanced_scores(
    feat_df.copy(),
    weights=norm_weights,
    candidate="candidate_b",
    is_improved=True,
    min_stores=1,
    discount_factor=discount_factor_val,
)
cand_b_ranked = rank_locations(cand_b_scored)

# 3. 활성 모델 선택
if model_mode == MODEL_MODE_BASELINE:
    raw_base_scored = compute_total_score(calculate_component_scores(feat_df.copy()), weights=norm_weights)
    active_ranked = rank_locations(raw_base_scored)
    # Option B: Baseline 출력 스키마 통일 (is_unentered 및 market_status 필드 보완)
    active_ranked["is_unentered"] = active_ranked["cat_store_count"].fillna(0).lt(1)
    active_ranked["market_status"] = np.where(
        ~active_ranked["is_unentered"],
        "기준선 분석 대상 지역",
        "해당 업종 점포 미확인 지역"
    )
elif model_mode == MODEL_MODE_SUBWAY_IMPROVED:
    active_ranked = base_ranked
else:  # Default: MODEL_MODE_INTEGRATED (Candidate B)
    active_ranked = cand_b_ranked

# 상세 분석은 추천 필터와 무관하게 선택 모델의 150개 행정동 전체를 제공한다.
detail_ranked = active_ranked.copy()

if filter_unentered_val:
    # Option A & B 통합 안전 가드: is_unentered 및 점포수 기준 완전 제외
    if "is_unentered" in active_ranked.columns:
        unentered_mask = active_ranked["is_unentered"].astype(bool)
    else:
        unentered_mask = active_ranked["cat_store_count"].fillna(0).lt(1)
    active_ranked = active_ranked[~unentered_mask].reset_index(drop=True)
    active_ranked["rank"] = range(1, len(active_ranked) + 1)

active_top5 = active_ranked.head(5)


def generate_active_explanation(row):
    """Return the explanation generator matching the active model branch."""
    if is_integrated_mode:
        return generate_enhanced_explanation(row, meta)
    if is_improved_mode:
        return generate_improved_explanation(row, meta)
    return generate_explanation(row, meta)

# ----------------------------------------------------
# 5. Header 및 서비스 핵심 설명
# ----------------------------------------------------
render_html(f"""
<section class="hero-banner">
    <div class="hero-brand">
        <span class="hero-symbol">🗺️</span>
        <div class="hero-header-title">대구 소상공인 AI 상권·창업 입지 추천 서비스 <span style="font-size:1.02rem; font-weight:700; color:#93C5FD; margin-left:6px;">| 팀 말괄량이코물이</span></div>
    </div>
    <div class="hero-header-sub">
        업종과 목표 고객을 선택하면 대구 150개 행정동의 수요·경쟁·접근성·주차·업종 특화도를 종합 분석하여<br>
        개인화된 입지 적합도를 추천합니다.
    </div>
    <div class="hero-slogan">더 좋은 내일을 위한<br>스마트한 창업의 시작</div>
    <div class="hero-bank"><img src="{logo_data_uri}" alt="iM뱅크"></div>
</section>
""")

# 💡 AI가 하는 일 카드
render_html("""
<div class="info-card-blue">
    <div class="info-card-title">💡 AI가 하는 일 (추천 엔진 원리)</div>
    <div class="info-card-content">
        사용자가 입력한 업종·타깃 고객·개인화 가중치에 따라 150개 행정동의 실제 공공데이터를 분석하고
        수요·타깃·경쟁·교통·주차·업종 특화도를 종합하여 개인화된 입지 적합도를 계산합니다.
    </div>
    <div class="info-card-notice">
        ※ 실제 관측 데이터에 존재하지 않는 창업 성공률, 예상 매출, 대출 승인 확률 등의 가상 예측치는 생성하지 않습니다.
    </div>
</div>
""")

# ----------------------------------------------------
# 6. 핵심 데이터 KPI 카드 (실제 데이터셋 동적 집계)
# ----------------------------------------------------
kpi_dongs = len(df_dong)
kpi_stores = len(df_store)
kpi_subways = len(df_subway) if df_subway is not None else 0
kpi_bus_stops = int(df_dong["dong_bus_stop_count"].sum()) if "dong_bus_stop_count" in df_dong.columns else 3981
kpi_parking = int(df_dong["dong_total_parking_capacity"].sum())
kpi_pop = int(df_dong["pop_total"].sum())

render_html(f"""
<div class="kpi-container">
    <div class="kpi-card kpi-blue">
        <div class="kpi-label">📍 대구 행정동</div>
        <div class="kpi-val">{kpi_dongs}개 동</div>
        <div class="kpi-sub">군위군 포함 전역 분석</div>
    </div>
    <div class="kpi-card kpi-green">
        <div class="kpi-label">🏪 상가 데이터</div>
        <div class="kpi-val">{kpi_stores:,}건</div>
        <div class="kpi-sub">대구 상가·상권 데이터</div>
    </div>
    <div class="kpi-card kpi-purple">
        <div class="kpi-label">🚇🚌 대중교통망</div>
        <div class="kpi-val">{kpi_subways}역 · {kpi_bus_stops:,}개소</div>
        <div class="kpi-sub">도시철도+시내버스 통합</div>
    </div>
    <div class="kpi-card kpi-sky">
        <div class="kpi-label">🅿️ 주차 공급</div>
        <div class="kpi-val">{kpi_parking:,}면</div>
        <div class="kpi-sub">건축물대장 부설주차면</div>
    </div>
    <div class="kpi-card kpi-orange">
        <div class="kpi-label">👥 주민등록 인구</div>
        <div class="kpi-val">약 {kpi_pop/10000:.1f}만 명</div>
        <div class="kpi-sub">실인구: {kpi_pop:,}명</div>
    </div>
</div>
""")

# ----------------------------------------------------
# 7. Navigation Tabs (핵심 5개 탭 구조)
# ----------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏆 추천 결과",
    "🗺️ 지도 보기 · 상세 분석",
    "⚖️ 통합 대중교통 모델 vs 도시철도 중심 개선 모델",
    "🏦 iM뱅크 연계 로드맵",
    "🗄️ 데이터/분석 방법",
])

# ----------------------------------------------------
# 8. 6대 컴포넌트 카드 생성 헬퍼 함수
# ----------------------------------------------------
def build_component_cards_html(row):
    """6대 컴포넌트 점수 상태(🟢/🟡/🔴) 통일 카드 HTML 생성"""
    comps = [
        ("수요", row["demand_score"]),
        ("타깃 적합도", row["target_fit_score"]),
        ("경쟁 기회도", row["competition_score"]),
        ("교통 접근성", row["accessibility_score"]),
        ("주차 공급", row["parking_score"]),
        ("업종 특화도", row["industry_fit_score"]),
    ]
    
    cards = []
    for name, sc in comps:
        st_info = get_score_status(sc)
        card_html = f"""
        <div style='background-color: {st_info["bg"]}; border: 1.5px solid {st_info["border"]}; border-radius: 12px; padding: 10px 8px; text-align: center;'>
            <div style='font-size: 0.76rem; font-weight: 600; color: #475569; margin-bottom: 2px;'>{name}</div>
            <div style='font-size: 1.25rem; font-weight: 800; color: {st_info["text"]}; letter-spacing: -0.02em;'>{sc:.1f}</div>
            <div style='display: inline-block; font-size: 0.72rem; font-weight: 700; color: {st_info["text"]}; background-color: #FFFFFF; border: 1px solid {st_info["border"]}; padding: 1px 6px; border-radius: 10px; margin-top: 3px;'>
                {st_info["full_badge"]}
            </div>
        </div>
        """
        cards.append(card_html)
        
    return f"""
    <div style='display: grid; grid-template-columns: repeat(6, 1fr); gap: 8px; margin: 12px 0 14px 0;'>
        {"".join(cards)}
    </div>
    """

def get_dong_strengths_and_cautions(row, meta, exp_dict):
    """
    6대 점수 기반 강점(>=70), 보통(40~69.99), 취약(<40) 동적 자동 분류
    """
    comps = [
        ("수요", row["demand_score"], "배후 주민등록 인구와 점포 규모 지표가"),
        ("타깃 적합도", row["target_fit_score"], f"타깃 고객층({meta['target_demographic_label']})의 집적도와 비중이"),
        ("경쟁 기회도", row["competition_score"], "선택 업종 점포 대비 배후 타깃인구 지표가"),
        ("교통 접근성", row["accessibility_score"], "도시철도·시내버스 접근성과 일평균 승하차 규모가"),
        ("주차 공급", row["parking_score"], "건축물대장 부설주차면 공급 여건이"),
        ("업종 특화도", row["industry_fit_score"], f"해당 업종({meta['industry_label']}) LQ 백분위가"),
    ]
    
    strong_items = []
    normal_items = []
    weak_items = []
    
    for name, sc, desc in comps:
        if sc >= 70.0:
            strong_items.append((name, sc, desc))
        elif sc < 40.0:
            weak_items.append((name, sc, desc))
        else:
            normal_items.append((name, sc, desc))
            
    return strong_items, normal_items, weak_items

# ----------------------------------------------------
# TAB 1: 추천 결과 & 상권 지도 (세로형 구조: 1위 -> 지도 -> 2~5위)
# ----------------------------------------------------
with tab1:
    # ====================================================
    # SECTION 1: 🥇 1위 추천 Hero Card (전체 너비)
    # ====================================================
    try:
        selected_rank = int(st.query_params.get("selected_rank", "1"))
    except (TypeError, ValueError):
        selected_rank = 1
    selected_rank = min(max(selected_rank, 1), len(active_top5))
    top1_row = active_top5.iloc[selected_rank - 1]
    top1_adm_raw = str(top1_row["adm_nm"])
    top1_adm = clean_markdown_to_html(top1_adm_raw)
    top1_score = float(top1_row["total_score"])
    top1_stores = int(top1_row["cat_store_count"])
    top1_gu_raw = top1_adm_raw.split()[1] if len(top1_adm_raw.split()) > 1 else "대구광역시"
    top1_gu = clean_markdown_to_html(top1_gu_raw)
    industry_label_html = clean_markdown_to_html(meta["industry_label"])
    target_label_html = clean_markdown_to_html(meta["target_demographic_label"])
    
    top1_exp = generate_active_explanation(top1_row)
    if is_integrated_mode:
        top1_mkt = str(top1_row.get("market_status", "해당 업종 점포 확인 지역"))
        top1_mkt_html = clean_markdown_to_html(top1_mkt)
        top1_badge = (
            f'<span class="badge-market-validated">🟢 {top1_mkt_html} (점포 {top1_stores}개)</span>'
            if not bool(top1_row.get("is_unentered", False))
            else f'<span class="badge-market-unentered">🟡 {top1_mkt_html}</span>'
        )
    elif is_improved_mode:
        top1_mkt = str(top1_row.get("market_status", "해당 업종 점포 확인 지역"))
        top1_mkt_html = clean_markdown_to_html(top1_mkt)
        top1_badge = (
            f'<span class="badge-market-validated">🟢 {top1_mkt_html} (점포 {top1_stores}개)</span>'
            if not bool(top1_row.get("is_unentered", False))
            else f'<span class="badge-market-unentered">🟡 {top1_mkt_html}</span>'
        )
    else:
        top1_badge = f'<span class="badge-market-validated">기준선 분석 (점포 {top1_stores}개)</span>'
        
    top1_comp_grid = build_component_cards_html(top1_row)

    # Reference-style above-the-fold summary: Top 5 cards + map.
    component_labels = [
        ("수요 기반 양호", "demand_score"),
        ("타깃 인구 비중 양호", "target_fit_score"),
        ("경쟁 여건 양호", "competition_score"),
        ("대중교통 접근 우수", "accessibility_score"),
        ("주차 여건 양호", "parking_score"),
        ("업종 특화도 높음", "industry_fit_score"),
    ]
    compact_cards = []
    for _, compact_row in active_top5.iterrows():
        compact_rank = int(compact_row["rank"])
        compact_name = clean_markdown_to_html(compact_row["adm_nm"])
        adm_parts = str(compact_row["adm_nm"]).split()
        compact_short = clean_markdown_to_html(" ".join(adm_parts[1:] if len(adm_parts) > 1 else adm_parts))
        best_reasons = sorted(component_labels, key=lambda item: compact_row[item[1]], reverse=True)[:3]
        reason_html = "".join(f"✓ {label}<br>" for label, _ in best_reasons)
        card_class = "compact-rank-card"
        if compact_rank == 1:
            card_class += " first"
        if compact_rank == selected_rank:
            card_class += " selected"
        compact_cards.append(f"""
        <a class="compact-rank-link" href="?selected_rank={compact_rank}#recommendation-detail" target="_self" aria-label="{compact_rank}위 {compact_name} 상세 보기">
            <div class="{card_class}">
                <span class="rank-ball">{compact_rank}</span>
                <div class="compact-name" title="{compact_name}">{compact_short}</div>
                <div class="compact-score-label">종합 적합도</div>
                <div class="compact-score">{compact_row['total_score']:.2f}점</div>
                <span class="compact-grade">{'매우 우수' if compact_rank == 1 else '우수'}</span>
                <div class="compact-reason-title">주요 추천 이유</div>
                <div class="compact-reason">{reason_html}</div>
            </div>
        </a>
        """)

    gdf_map = gdf_dong.merge(
        active_ranked[["adm_cd2", "total_score", "rank", "cat_store_count"]],
        on="adm_cd2", how="left"
    )
    gdf_map["total_score"] = gdf_map["total_score"].fillna(0.0)
    gdf_map["rank"] = gdf_map["rank"].fillna(999).astype(int)

    summary_left, summary_right = st.columns([1.62, 1], gap="small")
    with summary_left:
        render_html(f"""
        <div class="dashboard-panel">
            <div class="panel-head"><span>🏆 Top 5 추천 지역</span><span class="panel-chip">업종: {industry_label_html} · 타깃: {target_label_html}</span></div>
            <div class="compact-top-grid">{''.join(compact_cards)}</div>
        </div>
        """)
    with summary_right:
        render_html("""<div class="panel-head" style="background:#fff;border:1px solid #DDE7F2;border-bottom:0;border-radius:11px 11px 0 0;padding:13px 14px;margin:0;"><span>🗺️ 대구 상권 지도</span><span class="panel-chip">★ 추천지역 · ● 도시철도</span></div>""")
        compact_map = folium.Map(location=[35.8714, 128.6014], zoom_start=10, tiles="OpenStreetMap", control_scale=False)
        folium.Choropleth(
            geo_data=gdf_map.to_json(), data=gdf_map,
            columns=["adm_cd2", "total_score"], key_on="feature.properties.adm_cd2",
            fill_color="YlGnBu", fill_opacity=0.58, line_opacity=0.35,
        ).add_to(compact_map)
        for _, map_row in gdf_map[gdf_map["rank"] <= 5].iterrows():
            sub_c = int(map_row.get("dong_station_count", 0)) if "dong_station_count" in map_row else 0
            bus_c = int(map_row.get("dong_bus_stop_count", 0)) if "dong_bus_stop_count" in map_row else 0
            folium.Marker(
                [map_row["lat"], map_row["lng"]],
                tooltip=f"{int(map_row['rank'])}위 {html.escape(str(map_row['adm_nm']), quote=True)} ({map_row['total_score']:.1f}점 | 철도 {sub_c}역·버스 {bus_c}개소)",
                icon=folium.Icon(color="orange" if int(map_row["rank"]) == 1 else "blue", icon="star", prefix="fa"),
            ).add_to(compact_map)
        map_html = compact_map.get_root().render()
        if hasattr(st, "iframe"):
            st.iframe(map_html, height=302)
        else:
            components.html(map_html, height=302)

    render_html("""<div id="recommendation-detail" style="height:8px;"></div>""")
    
    render_html(f"""
    <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;'>
        <div style='display: flex; align-items: center; gap: 8px;'>
            <span style='font-size: 1.3rem; font-weight: 800; color: #0F172A;'>🏆 추천 결과 종합</span>
            <span style='font-size: 0.85rem; color: #64748B;'>대구시 150개 행정동 전수 분석</span>
        </div>
        <div style='display: flex; gap: 6px;'>
            <span style='background-color: #EFF6FF; color: #1E40AF; padding: 4px 10px; border-radius: 12px; font-size: 0.8rem; font-weight: 700;'>
                업종: {industry_label_html}
            </span>
            <span style='background-color: #ECFDF5; color: #065F46; padding: 4px 10px; border-radius: 12px; font-size: 0.8rem; font-weight: 700;'>
                타깃: {target_label_html}
            </span>
            <span style='background-color: #F1F5F9; color: #475569; padding: 4px 10px; border-radius: 12px; font-size: 0.8rem; font-weight: 700;'>
                모델: {'대중교통 통합 (권장)' if is_integrated_mode else ('도시철도 개선' if is_improved_mode else '기준선')}
            </span>
        </div>
    </div>
    
    <div class="top1-hero-card">
        <div class="top1-header-row">
            <div>
                <span class="top1-badge-gold">🏅 {selected_rank}위 추천 입지</span>
                <div style='font-size: 1.55rem; font-weight: 800; color: #0F172A; margin-top: 6px;'>
                    {top1_adm}
                </div>
                <div style='font-size: 0.85rem; color: #64748B; margin-top: 2px;'>
                    대구광역시 {top1_gu} 관내 · {top1_badge}
                </div>
                <div style='display: flex; gap: 8px; font-size: 0.78rem; margin: 8px 0 2px 0; flex-wrap: wrap;'>
                    <span style='background: #EFF6FF; border: 1px solid #BFDBFE; color: #1E40AF; padding: 3px 8px; border-radius: 6px; font-weight: 600;'>
                        🚇 도시철도: <b>{int(top1_row.get("dong_station_count", 0))}개역</b> (일평균 승하차 {float(top1_row.get("dong_daily_ridership", 0)):,.0f}명)
                    </span>
                    <span style='background: #F0FDF4; border: 1px solid #BBF7D0; color: #166534; padding: 3px 8px; border-radius: 6px; font-weight: 600;'>
                        🚌 시내버스: <b>{int(top1_row.get("dong_bus_stop_count", 0))}개소</b> (일평균 승하차 {float(top1_row.get("dong_daily_bus_total", 0)):,.0f}명 · 최근접 {float(top1_row.get("avg_dist_to_bus_m", 0)):.0f}m)
                    </span>
                </div>
            </div>
            <div style='text-align: right;'>
                <div style='font-size: 0.82rem; font-weight: 700; color: #B45309;'>입지 적합도</div>
                <div class="top1-score-tag">{top1_score:.2f}점</div>
                <div style='font-size: 0.75rem; color: #94A3B8;'>100점 만점 기준</div>
            </div>
        </div>
        
        <div style='display: flex; justify-content: space-between; align-items: center; margin: 10px 0 4px 0;'>
            <div style='font-size: 0.82rem; font-weight: 700; color: #475569;'>6대 컴포넌트 적합도 진단</div>
            <div style='font-size: 0.74rem; color: #64748B;'>
                <span style='margin-right: 6px;'>🟢 추천 <b>70~100</b></span>
                <span style='margin-right: 6px;'>🟡 보통 <b>40~69</b></span>
                <span>🔴 비추천 <b>0~39</b></span>
            </div>
        </div>
        
        {top1_comp_grid}
    </div>
    """)
    
    # 1위 동적 강점 및 취약점 분류
    strong_items, normal_items, weak_items = get_dong_strengths_and_cautions(top1_row, meta, top1_exp)
    
    # 강점 불릿 생성
    str_bullets = ""
    for name, sc, desc in strong_items:
        desc_html = clean_markdown_to_html(desc)
        str_bullets += f"<li><b>{name}</b> ({sc:.1f}점): {desc_html} 대구시 상위권으로 우수합니다.</li>"
    if not str_bullets and top1_exp["strengths"]:
        str_bullets = "".join([f"<li>{clean_markdown_to_html(s)}</li>" for s in top1_exp["strengths"][:3]])
    elif not str_bullets:
        str_bullets = "<li>6대 컴포넌트 전반이 고르게 우수한 상권입니다.</li>"
        
    # 취약점 / 확인 필요 사항 불릿 생성
    caut_bullets = ""
    if weak_items:
        for name, sc, desc in weak_items:
            desc_html = clean_markdown_to_html(desc)
            caut_bullets += f"<li style='color: #B91C1C;'><b>⚠️ [취약] {name} ({sc:.1f}점)</b>: {desc_html} 40점 미만으로 낮아 면밀한 현장 보완책이 필요합니다.</li>"
    for name, sc, desc in normal_items:
        caut_bullets += f"<li><b>{name} ({sc:.1f}점)</b>: 대구시 평균 수준(40~70점 구간)입니다.</li>"
    if top1_exp["cautions"]:
        for c in top1_exp["cautions"][:2]:
            caut_bullets += f"<li>{clean_markdown_to_html(c)}</li>"
    if not caut_bullets:
        caut_bullets = "<li>특별한 감점 요인이 없는 안정적인 입지 환경입니다.</li>"
        
    render_html(f"""
    <div style='background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px; padding: 14px 18px; margin-bottom: 24px;'>
        <div style='font-size: 0.88rem; font-weight: 700; color: #15803D; margin-bottom: 4px;'>✓ 데이터 실측 강점 (70점 이상 지표)</div>
        <ul style='font-size: 0.84rem; color: #334155; margin: 0 0 10px 0; padding-left: 18px; line-height: 1.5;'>
            {str_bullets}
        </ul>
        <div style='font-size: 0.88rem; font-weight: 700; color: #B45309; margin-bottom: 4px;'>⚠️ 확인이 필요한 사항 (보통 및 취약 지표)</div>
        <ul style='font-size: 0.84rem; color: #334155; margin: 0; padding-left: 18px; line-height: 1.5;'>
            {caut_bullets}
        </ul>
    </div>
    """)
    
    # ====================================================
    # SECTION 2: 🗺️ 상권 지도 (전체 너비 + 직결 설명)
    # ====================================================
    # 지도는 상단 Top 5 옆 compact_map으로 통합 렌더링합니다.

# ----------------------------------------------------
# TAB 2: 추천 지역 정밀 분석
# ----------------------------------------------------
with tab2:
    st.markdown("### 🔍 추천 지역 정밀 분석")
    st.markdown("Top 5 추천 입지 또는 대구시 내 관심 행정동을 선택하여 심층 공간 통계와 관측 데이터를 정밀 진단합니다.")
    
    top5_adm_list = active_top5["adm_nm"].tolist()
    remaining_adm_list = [name for name in detail_ranked["adm_nm"].tolist() if name not in top5_adm_list]
    detail_labels = [f"Top {rank} · {name}" for rank, name in enumerate(top5_adm_list, start=1)] + remaining_adm_list
    detail_name_by_label = {
        **{f"Top {rank} · {name}": name for rank, name in enumerate(top5_adm_list, start=1)},
        **{name: name for name in remaining_adm_list},
    }
    chosen_label = st.selectbox("정밀 진단할 행정동 선택", options=detail_labels, index=0)
    chosen_dong = detail_name_by_label[chosen_label]
    chosen_dong_html = clean_markdown_to_html(chosen_dong)
    target_row = detail_ranked[detail_ranked["adm_nm"] == chosen_dong].iloc[0]
    
    # 상단 점수 기준 Legend
    render_html("""
    <div style='display: flex; justify-content: space-between; align-items: center; margin: 10px 0 6px 0;'>
        <div style='font-size: 0.95rem; font-weight: 800; color: #0F172A;'>6대 컴포넌트 적합도 점수 상태</div>
        <div style='font-size: 0.78rem; color: #64748B;'>
            <span style='margin-right: 8px;'>🟢 추천 <b>70~100</b></span>
            <span style='margin-right: 8px;'>🟡 보통 <b>40~69</b></span>
            <span>🔴 비추천 <b>0~39</b></span>
        </div>
    </div>
    """)
    
    detail_comp_grid = build_component_cards_html(target_row)
    render_html(detail_comp_grid)
    
    # 선택 동 취약점 자동 분류 표시
    chosen_exp = generate_active_explanation(target_row)
    t_strong, t_normal, t_weak = get_dong_strengths_and_cautions(target_row, meta, chosen_exp)
    
    if t_weak:
        weak_str = ", ".join([f"<b>{w[0]} ({w[1]:.1f}점)</b>" for w in t_weak])
        render_html(f"""
        <div style='background-color: #FEF2F2; border: 1px solid #FCA5A5; border-left: 4px solid #EF4444; border-radius: 10px; padding: 12px 16px; margin-bottom: 16px;'>
            <div style='font-size: 0.88rem; font-weight: 700; color: #B91C1C; margin-bottom: 2px;'>
                ⚠️ 우선 확인할 취약 항목 (40점 미만 지표)
            </div>
            <div style='font-size: 0.84rem; color: #7F1D1D; line-height: 1.5;'>
                {chosen_dong_html} 상권은 {weak_str} 항목이 상대적으로 취약합니다. 창업 계획 수립 시 차별화된 마케팅이나 보완책이 권장됩니다.
            </div>
        </div>
        """)
        
    c_chart, c_table = st.columns([1, 1], gap="medium")
    
    with c_chart:
        st.markdown("##### 📈 6대 컴포넌트 상대 적합도")
        chart_data = pd.DataFrame({
            "컴포넌트": ["수요", "타깃 적합", "경쟁 기회", "교통 접근", "주차 공급", "업종 특화"],
            "적합도 점수": [
                target_row["demand_score"],
                target_row["target_fit_score"],
                target_row["competition_score"],
                target_row["accessibility_score"],
                target_row["parking_score"],
                target_row["industry_fit_score"]
            ]
        }).set_index("컴포넌트")
        st.bar_chart(chart_data, height=310)
        
    with c_table:
        st.markdown("##### 📋 핵심 관측 데이터 정량표")
        pop_tot = int(target_row["pop_total"])
        tgt_pop = int(target_row["target_pop"])
        tgt_ratio = target_row["target_ratio"] * 100.0
        tot_stores = int(target_row["total_stores"])
        cat_stores = int(target_row["cat_store_count"])
        sub_dist = float(target_row["cat_avg_subway_dist"])
        sub_riders = float(target_row["dong_daily_ridership"])
        sub_cnt = int(target_row.get("dong_station_count", 0))
        bus_cnt = int(target_row.get("dong_bus_stop_count", 0))
        bus_riders = float(target_row.get("dong_daily_bus_total", 0))
        bus_dens = float(target_row.get("dong_bus_stop_density", 0))
        bus_dist = float(target_row.get("avg_dist_to_bus_m", 0))
        park_tot = int(target_row["dong_total_parking_capacity"])
        park_store = float(target_row["parking_capacity_per_store"])
        lq_val = float(target_row["location_quotient"])
        comp_300 = float(target_row["cat_avg_comp_300m"])
        
        detail_data = pd.DataFrame([
            {"구분": "인구 수요", "관측 지표": "배후 주민등록 인구", "실측 수치": f"{pop_tot:,}명"},
            {"구분": "타깃 인구", "관측 지표": f"{meta['target_demographic_label']} 규모 (비중)", "실측 수치": f"{tgt_pop:,}명 ({tgt_ratio:.1f}%)"},
            {"구분": "상권 규모", "관측 지표": "전체 점포수", "실측 수치": f"{tot_stores:,}개소"},
            {"구분": "동종 집적", "관측 지표": f"{meta['industry_label']} 점포수 (특화도 LQ)", "실측 수치": f"{cat_stores}개소 (LQ: {lq_val:.2f})"},
            {"구분": "직접 경쟁", "관측 지표": "반경 300m 내 동종업종 밀집 평균", "실측 수치": f"{comp_300:.1f}개"},
            {"구분": "철도 인프라", "관측 지표": "최인접 도시철도역 평균 거리 (역 수)", "실측 수치": f"{sub_dist:.0f}m ({sub_cnt}개역)"},
            {"구분": "철도 이용량", "관측 지표": "관내 도시철도 일평균 승하차 인원", "실측 수치": f"{sub_riders:,.0f}명/일"},
            {"구분": "버스 인프라", "관측 지표": "관내 시내버스 정류소 수 (면적당 밀도)", "실측 수치": f"{bus_cnt}개소 ({bus_dens:.1f}개/km²)"},
            {"구분": "버스 이용량", "관측 지표": "관내 시내버스 일평균 승하차 인원 (최근접 거리)", "실측 수치": f"{bus_riders:,.0f}명/일 (평균 {bus_dist:.0f}m)"},
            {"구분": "주차 여건", "관측 지표": "동 총 부설주차면수 (점포당 면수)", "실측 수치": f"{park_tot:,}면 (점포당 {park_store:.2f}면)"},
        ])
        st.dataframe(detail_data, width="stretch", hide_index=True)
        st.caption("※ 도시철도는 2026년 1~7월 일별 관측(212일), 시내버스는 같은 기간의 월별 집계를 212일로 나눈 일평균 기준입니다.")

    if cat_stores == 0:
        render_html("""
        <div style='background-color: #FFFBEB; border: 1px solid #FDE68A; border-left: 4px solid #F59E0B; border-radius: 10px; padding: 14px 18px; margin-top: 14px;'>
            <div style='font-size: 0.88rem; font-weight: 700; color: #92400E; margin-bottom: 2px;'>
                🟡 해당 업종 점포 미확인 지역 안내
            </div>
            <div style='font-size: 0.84rem; color: #78350F; line-height: 1.5;'>
                현재 데이터에서 해당 업종 점포가 확인되지 않습니다. 경쟁이 낮을 가능성이 있는 반면, 
                시장 형성이 충분하지 않거나 용도지역 인허가 제한이 있을 수 있으므로 신중한 현장 확인이 필요합니다.
            </div>
        </div>
        """)

# ----------------------------------------------------
# TAB 3: 통합 대중교통 모델 vs 도시철도 중심 개선 모델 비교
# ----------------------------------------------------
with tab3:
    st.markdown("### ⚖️ 통합 대중교통 모델 (권장) vs 도시철도 중심 개선 모델 정량 비교")
    st.markdown(
        f"""
        - **통합 대중교통 모델 (권장)**: 도시철도(70%)와 시내버스(30%) 승하차 및 정류소 데이터를 개별 백분위 정규화(Percentile Rank)로 결합합니다. (해당 업종 점포 미확인 지역 보정 $\\alpha={discount_factor_val:.2f}$)
        - **도시철도 중심 개선 모델**: 도시철도 94개 역 중심으로 접근성을 평가하며 동일한 보정 계수 $\\alpha={discount_factor_val:.2f}$을 적용합니다.  
        """
    )
    
    df_compare = base_ranked[[
        "adm_cd2", "adm_nm", "rank", "total_score", "accessibility_score", "competition_score", "cat_store_count", "dong_station_count"
    ]].rename(
        columns={"rank": "rank_base", "total_score": "score_base", "accessibility_score": "access_base", "competition_score": "comp_base"}
    ).merge(
        cand_b_ranked[[
            "adm_cd2", "rank", "total_score", "accessibility_score", "competition_score", "market_status", "dong_daily_bus_total", "dong_bus_stop_count"
        ]].rename(
            columns={"rank": "rank_cand", "total_score": "score_cand", "accessibility_score": "access_cand", "competition_score": "comp_cand"}
        ),
        on="adm_cd2"
    )
    df_compare["rank_change"] = df_compare["rank_base"] - df_compare["rank_cand"]
    df_compare["access_change"] = (df_compare["access_cand"] - df_compare["access_base"]).round(2)
    
    rho, _ = spearmanr(df_compare["rank_base"], df_compare["rank_cand"])
    t10_b = set(df_compare.sort_values("rank_base").head(10)["adm_cd2"])
    t10_c = set(df_compare.sort_values("rank_cand").head(10)["adm_cd2"])
    t10_overlap = len(t10_b & t10_c)
    
    no_subway_mask = df_compare["dong_station_count"] == 0
    no_subway_lift = (df_compare.loc[no_subway_mask, "access_cand"].mean() - df_compare.loc[no_subway_mask, "access_base"].mean())
    
    c1, c2, c3 = st.columns(3)
    c1.metric("150개 동 순위 상관계수", f"ρ = {rho:.4f}", describe_rank_similarity(float(rho)))
    c2.metric("Top 10 일치수", f"{t10_overlap} / 10개", f"일치율 {t10_overlap*10}%")
    c3.metric("비역세권 91개 동 접근성 변화", f"Δ {no_subway_lift:+.2f}점", "도시철도 중심 평가 한계 보완")
    st.caption("※ 위 3대 정량 지표는 현재 선택된 업종·타깃·가중치 조건에서 실시간 산출된 비교 결과입니다.")
    
    st.markdown("#### 📋 Top 10 순위 비교표 (통합 모델 기준)")
    top10_comp = df_compare.sort_values("rank_cand").head(10)[[
        "rank_cand", "rank_base", "rank_change", "adm_nm", "score_cand", "score_base",
        "access_cand", "access_base", "dong_station_count", "dong_daily_bus_total", "market_status"
    ]].rename(columns={
        "rank_cand": "통합순위", "rank_base": "기준순위", "rank_change": "순위변동", "adm_nm": "행정동명",
        "score_cand": "통합총점", "score_base": "기준총점", "access_cand": "통합접근성", "access_base": "기준접근성",
        "dong_station_count": "철도역수", "dong_daily_bus_total": "버스일평균승하차", "market_status": "상권구분"
    })
    st.dataframe(top10_comp, width="stretch", hide_index=True)
    
    st.markdown("#### 🚌 비역세권(도시철도 미경유 91개 동) 순위 변화 지역")
    no_sub_gains = df_compare[no_subway_mask].sort_values("rank_change", ascending=False).head(5)[[
        "adm_nm", "rank_cand", "rank_base", "rank_change", "access_change", "dong_daily_bus_total", "dong_bus_stop_count"
    ]].rename(columns={
        "adm_nm": "행정동명", "rank_cand": "통합순위", "rank_base": "기준순위", "rank_change": "순위상승폭",
        "access_change": "접근성점수변화", "dong_daily_bus_total": "버스일평균승하차", "dong_bus_stop_count": "정류소수"
    })
    st.markdown("지하철역은 없으나 실제 버스 이용객이 활발한 핵심 골목상권이 합당한 대중교통 접근성을 재평가받은 결과입니다:")
    st.dataframe(no_sub_gains, width="stretch", hide_index=True)

    zero_cnt = (df_compare["cat_store_count"] == 0).sum()
    if zero_cnt > 0:
        st.markdown(f"#### 🔍 해당 업종 점포 미확인 지역의 교통 접근성 모델별 결과 비교 (현재 α={discount_factor_val:.2f})")
        st.caption("동일한 α 보정 조건에서 도시철도 중심 모델과 통합 대중교통 모델의 결과를 비교합니다. 할인 적용 전후 비교표가 아닙니다.")
        zero_sample = df_compare[df_compare["cat_store_count"] == 0].sort_values("rank_base").head(5)[[
            "adm_nm", "rank_base", "rank_cand", "score_base", "score_cand", "comp_base", "comp_cand"
        ]].rename(columns={
            "adm_nm": "행정동명", "rank_base": "기준선 순위", "rank_cand": "통합 모델 순위",
            "score_base": "기준 총점", "score_cand": "통합 총점", "comp_base": "기준 경쟁점수", "comp_cand": "통합 경쟁점수"
        })
        st.dataframe(zero_sample, width="stretch", hide_index=True)

# ----------------------------------------------------
# TAB 4: iM뱅크 금융 연계 로드맵
# ----------------------------------------------------
with tab4:
    st.markdown("### 🏦 iM뱅크 금융 연계 로드맵 & 데이터 거버넌스")
    render_html("""
    <p style="color:#475569; margin:0 0 14px;">
        AI 입지 추천을 바탕으로 향후 <b>iM뱅크(대구은행)와의 제휴 및 금융 API 연계</b>를 통해
        소상공인 금융상담 및 정책자금 연계로 확장하기 위한 4단계 사업 로드맵입니다.
    </p>
    """)
    
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        render_html("""
        <div class="step-card">
            <span class="step-badge-active">1단계: 현재 제공 (프로토타입)</span>
            <div style='font-size: 1.02rem; font-weight: 800; color: #0F172A; margin: 8px 0 4px 0;'>
                AI 상권·입지 분석
            </div>
            <div style='font-size: 0.82rem; color: #475569; line-height: 1.5;'>
                - 공공 빅데이터 기반 입지 추천<br>
                - 6대 다차원 상권 공간 진단<br>
                - 타깃 고객 및 경쟁 밀집도 제공
            </div>
        </div>
        """)
    with f2:
        render_html("""
        <div class="step-card">
            <span class="step-badge-future">2단계: 향후 확장 로드맵</span>
            <div style='font-size: 1.02rem; font-weight: 800; color: #0F172A; margin: 8px 0 4px 0;'>
                창업 비용 및 자금계획
            </div>
            <div style='font-size: 0.82rem; color: #475569; line-height: 1.5;'>
                - 희망 평수 및 보증금 기반 계획<br>
                - 인테리어/설비 창업비용 자가진단<br>
                - 초기 운전자금 필요액 산출 지원
            </div>
        </div>
        """)
    with f3:
        render_html("""
        <div class="step-card">
            <span class="step-badge-future">3단계: 향후 확장 로드맵</span>
            <div style='font-size: 1.02rem; font-weight: 800; color: #0F172A; margin: 8px 0 4px 0;'>
                정책자금 연계 안내
            </div>
            <div style='font-size: 0.82rem; color: #475569; line-height: 1.5;'>
                - 자기자본 대비 부족 자금 분석<br>
                - 대구시 소상공인 정책자금 안내<br>
                - 신용보증재단 특례보증 상담 연계
            </div>
        </div>
        """)
    with f4:
        render_html("""
        <div class="step-card">
            <span class="step-badge-future">4단계: 향후 확장 로드맵</span>
            <div style='font-size: 1.02rem; font-weight: 800; color: #0F172A; margin: 8px 0 4px 0;'>
                iM뱅크 금융상담 연계
            </div>
            <div style='font-size: 0.82rem; color: #475569; line-height: 1.5;'>
                - iM뱅크 제휴 금융상담 연계<br>
                - 인근 영업점 전문상담 연계 지원<br>
                - 상생 금융상품·우대혜택 연계 가능성 검토
            </div>
        </div>
        """)
        
    st.caption("※ 2~4단계는 향후 금융 API 및 iM뱅크와의 제휴를 통해 금융상담·정책자금 연계로 확장하기 위한 사업 로드맵입니다. 현재 프로토타입은 1단계 AI 입지 추천 기능을 제공합니다.")
    
    st.markdown("---")
    st.markdown("#### 🛡️ 데이터 거버넌스 및 신뢰성 공시 (투명한 한계 안내)")
    st.markdown("""
    1. **Ground Truth 부재**: 본 모델은 폐업률, 생존율, 실매출 등의 정답 레이블이 없는 공공 통계 데이터셋을 바탕으로 구축되었으므로, '창업 성공 확률'이나 '예상 매출'을 인위적으로 예측하지 않습니다.
    2. **상대적 입지 적합도**: 산출된 점수는 대구시 150개 행정동 내부에서의 '상대적 백분위 적합도(Suitability Score: 0~100)'입니다.
    3. **대중교통 데이터 정의**: 본 서비스의 교통 지표는 도시철도 94개 역의 2026년 1~7월 일별 관측과 시내버스 3,981개 정류소의 같은 기간 월별 집계를 212일 기준 일평균으로 환산한 승하차 인원을 개별 백분위 정규화(Percentile Rank)하여 가중합산(철도 70% + 버스 30%)한 상대적 접근성 지표입니다.
    4. **주차 공급 지표 한계**: 주차 데이터는 건축물대장 기반 부설주차장 수용능력 proxy 지표이므로, 실제 상가 방문 고객이 무료로 이용 가능한 전용 주차장 여부는 현장 실사가 필요합니다.
    5. **해당 업종 점포 미확인 지역 주의**: 현재 데이터에서 해당 업종 점포가 확인되지 않는 지역은 관측된 경쟁점포가 적지만, 수요 부재나 인허가 제한 가능성이 있으므로 현장조사가 필요합니다.
    """)

# ----------------------------------------------------
# TAB 5: 현재 조건의 행정동 데이터 및 CSV 다운로드
# ----------------------------------------------------
with tab5:
    result_count = len(active_ranked)
    total_dong_count = len(detail_ranked)
    st.markdown(f"### 📊 현재 조건 랭킹 데이터 {result_count}개 (전체 {total_dong_count}개 중 · {'대중교통 통합' if is_integrated_mode else ('도시철도 개선' if is_improved_mode else '기준선')})")
    
    export_cols = [
        "rank", "adm_nm", "total_score", "demand_score", "target_fit_score",
        "competition_score", "accessibility_score", "parking_score", "industry_fit_score"
    ]
    if "subway_accessibility_score" in active_ranked.columns:
        export_cols.append("subway_accessibility_score")
    if "bus_accessibility_score" in active_ranked.columns:
        export_cols.append("bus_accessibility_score")
    if "dong_station_count" in active_ranked.columns:
        export_cols.append("dong_station_count")
    if "dong_bus_stop_count" in active_ranked.columns:
        export_cols.append("dong_bus_stop_count")
    if "dong_daily_bus_total" in active_ranked.columns:
        export_cols.append("dong_daily_bus_total")
    export_cols.extend(["cat_store_count", "pop_total", "target_pop", "location_quotient"])
    
    col_rename = {
        "rank": "순위", "adm_nm": "행정동명", "total_score": "총점",
        "demand_score": "배후수요", "target_fit_score": "타깃적합", "competition_score": "경쟁기회",
        "accessibility_score": "대중교통접근", "parking_score": "주차공급", "industry_fit_score": "업종특화",
        "subway_accessibility_score": "철도접근점수", "bus_accessibility_score": "버스접근점수",
        "dong_station_count": "철도역수", "dong_bus_stop_count": "버스정류소수", "dong_daily_bus_total": "버스일평균승하차",
        "cat_store_count": "점포수", "pop_total": "총인구", "target_pop": "타깃인구", "location_quotient": "특화도(LQ)"
    }
    
    display_df = active_ranked[[c for c in export_cols if c in active_ranked.columns]].rename(columns=col_rename)
    
    search_dong = st.text_input("행정동 검색 (예: 신암4동, 감삼동, 범어1동, 진천동)", "").strip()
    if search_dong:
        filtered_display = display_df[
            display_df["행정동명"].astype(str).str.contains(search_dong, regex=False, na=False)
        ]
    else:
        filtered_display = display_df
        
    st.dataframe(filtered_display, width="stretch", hide_index=True)
    
    csv_data = display_df.to_csv(index=False).encode("utf-8-sig")
    safe_industry = re.sub(r"[^0-9A-Za-z가-힣_-]+", "_", ind_query).strip("_") or "industry"
    safe_target = re.sub(r"[^0-9A-Za-z가-힣_-]+", "_", target_query).strip("_") or "target"
    st.download_button(
        label=f"📥 현재 조건 {result_count}개 행정동 추천 데이터 CSV 다운로드",
        data=csv_data,
        file_name=f"daegu_ai_recommendation_{safe_industry}_{safe_target}.csv",
        mime="text/csv",
    )

render_html("""
<div style='text-align: center; font-size: 0.82rem; color: #94A3B8; padding: 16px 0 6px 0;'>
    대구 소상공인 AI 상권·창업 입지 추천 서비스 | 팀 말괄량이코물이 | Powered by Python, Streamlit & Folium | 2026 AI Blockchain Challenge in Daegu 출품작
</div>
""")
