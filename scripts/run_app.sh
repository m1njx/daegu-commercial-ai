#!/usr/bin/env bash
# ==============================================================================
# One-Click Launch Script for Streamlit Dashboard (macOS / Linux)
# Team: 말괄량이코물이
# Project: 대구 소상공인 AI 상권·창업 입지 추천 서비스
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "======================================================================"
echo "대구 소상공인 AI 상권·창업 입지 추천 서비스 시작 중... (팀: 말괄량이코물이)"
echo "프로젝트 위치: $PROJECT_ROOT"
echo "======================================================================"

# 가상환경 활성화 (존재할 경우)
if [ -d "$PROJECT_ROOT/.venv" ]; then
    echo "[*] 가상환경 감지됨: .venv 활성화"
    source "$PROJECT_ROOT/.venv/bin/activate"
elif [ -d "$PROJECT_ROOT/venv" ]; then
    echo "[*] 가상환경 감지됨: venv 활성화"
    source "$PROJECT_ROOT/venv/bin/activate"
fi

# Streamlit 실행
echo "[*] Streamlit 애플리케이션 실행 중 (app/app.py)..."
python3 -m streamlit run "$PROJECT_ROOT/app/app.py" --server.port 8501
