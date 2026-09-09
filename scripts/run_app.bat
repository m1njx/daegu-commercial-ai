@echo off
REM ==============================================================================
REM One-Click Launch Script for Streamlit Dashboard (Windows)
REM Team: 말괄량이코물이
REM Project: 대구 소상공인 AI 상권·창업 입지 추천 서비스
REM ==============================================================================

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%.."

echo ======================================================================
echo 대구 소상공인 AI 상권·창업 입지 추천 서비스 시작 중... (팀: 말괄량이코물이)
echo ======================================================================

IF EXIST ".venv\Scripts\activate.bat" (
    echo [*] 가상환경 감지됨: .venv 활성화
    call .venv\Scripts\activate.bat
) ELSE (
    IF EXIST "venv\Scripts\activate.bat" (
        echo [*] 가상환경 감지됨: venv 활성화
        call venv\Scripts\activate.bat
    )
)

echo [*] Streamlit 애플리케이션 실행 중 (app/app.py)...
python -m streamlit run app\app.py --server.port 8501
pause
