# -*- coding: utf-8 -*-
"""
scripts/verify_browser_ui.py
Playwright를 이용한 실제 Streamlit 브라우저 렌더링, 콘솔 에러, 레이아웃 및 탭 전수 QA
"""

import sys
import os
import time
import socket
import subprocess
import tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]

def run_browser_qa():
    print("=" * 70)
    print("브라우저 실제 렌더링 및 UI 전수 QA 시작")
    print("=" * 70)
    
    proc = None
    if "DAEGU_APP_URL" not in os.environ:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if sock.connect_ex(("localhost", 8502)) != 0:
            print("[*] Starting Streamlit test server on port 8502...")
            proc = subprocess.Popen(
                [sys.executable, "-m", "streamlit", "run", str(ROOT / "app/app.py"), "--server.port", "8502", "--server.headless", "true"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=str(ROOT)
            )
            time.sleep(6)
        sock.close()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            # 1920x1080 해상도
            page = browser.new_page(viewport={"width": 1920, "height": 1080})
            
            console_errors = []
            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
            page.on("pageerror", lambda err: console_errors.append(str(err)))
            
            url = os.environ.get("DAEGU_APP_URL", "http://localhost:8502")
            print(f"[*] Navigating to {url}...")
            page.goto(url, wait_until="networkidle", timeout=45000)
            time.sleep(3) # Ensure folium and charts fully settle
            
            # 1. First impression & Header
            title = page.title()
            print(f"[1] Page Title: {title}")
            header_text = page.locator(".hero-header-title").inner_text()
            print(f"[1] Header Text: {header_text}")
            assert "대구 소상공인 AI 상권·창업 입지 추천 서비스" in header_text
            assert "팀 말괄량이코물이" in header_text
            
            # 2. Check Top 1 Hero card
            top1_adm = page.locator(".top1-hero-card .top1-header-row div:nth-child(1) div:nth-child(2)").inner_text()
            top1_score = page.locator(".top1-score-tag").inner_text()
            print(f"[2] Default Top 1: {top1_adm} ({top1_score})")
            assert "신암4동" in top1_adm, f"Top 1 불일치: {top1_adm}"
            assert "77.75" in top1_score, f"Top 1 점수 불일치: {top1_score}"
            
            # 3. Check Compact Top 5 Cards
            cards = page.locator(".compact-rank-card").all()
            print(f"[3] Top 5 Compact Cards count: {len(cards)}")
            assert len(cards) == 5, f"Top 5 카드 수 오류: {len(cards)}"
            card_names = [c.locator(".compact-name").inner_text() for c in cards]
            print(f"[3] Top 5 Compact Cards: {card_names}")
            assert "신암4동" in card_names[0]
            
            # 4. Check Folium map in Tab 1
            print("[4] Auditing Map in Tab 1...")
            map_iframe = page.locator("iframe").first
            assert map_iframe.is_visible(), "Folium 지도 iframe 미렌더링"
            print("  -> Folium Map iframe 렌더링 정상")
            
            # 5. Check Tab 3 (모델 비교)
            print("[5] Auditing Tab 3 (모델 비교)...")
            tab3_btn = page.locator("[role='tab']", has_text="모델")
            if not tab3_btn.is_visible():
                tab_btns = page.locator("[role='tab']").all()
                tab3_btn = tab_btns[2]
            tab3_btn.click()
            time.sleep(2)
            tab3_content = page.content()
            assert "150개 동 순위 상관계수" in tab3_content
            assert "접근성 변화" in tab3_content
            print("  -> Tab 3 렌더링 정상 확인")
            
            # 6. Check Tab 4 (iM뱅크 금융 연계 로드맵)
            print("[6] Auditing Tab 4 (iM뱅크 금융 연계 로드맵)...")
            tab4_btn = page.locator("[role='tab']", has_text="iM뱅크")
            if not tab4_btn.is_visible():
                tab_btns = page.locator("[role='tab']").all()
                tab4_btn = tab_btns[3]
            tab4_btn.click()
            time.sleep(2)
            tab4_content = page.content()
            assert "1단계: 현재 제공 (프로토타입)" in tab4_content, "1단계 배지 누락"
            assert "4단계: 향후 확장 로드맵" in tab4_content, "4단계 배지 누락"
            assert "상생 금융상품·우대혜택 연계 가능성 검토" in tab4_content, "4단계 상생 검토 문구 누락"
            assert "※ 2~4단계는 향후 금융 API 및 iM뱅크와의 제휴를 통해 금융상담·정책자금 연계로 확장하기 위한 사업 로드맵입니다. 현재 프로토타입은 1단계 AI 입지 추천 기능을 제공합니다." in tab4_content, "핵심 로드맵 캡션 누락"
            print("  -> Tab 4 렌더링 및 정제 문구 정상 확인")
            
            # 7. Check Tab 5 (데이터 내보내기 & CSV)
            print("[7] Auditing Tab 5 (데이터 내보내기)...")
            tab5_btn = page.locator("[role='tab']", has_text="데이터/분석")
            if not tab5_btn.is_visible():
                tab_btns = page.locator("[role='tab']").all()
                tab5_btn = tab_btns[4]
            tab5_btn.click()
            time.sleep(2)
            tab5_content = page.content()
            assert "현재 조건 랭킹 데이터 150개 (전체 150개 중" in tab5_content
            assert "현재 조건 150개 행정동 추천 데이터 CSV 다운로드" in tab5_content
            print("  -> Tab 5 렌더링 정상 확인")
            
            # 8. Check responsive at 1440x900
            print("[8] Checking 1440x900 viewport...")
            page.set_viewport_size({"width": 1440, "height": 900})
            time.sleep(1)
            # return to Tab 1
            tab1_btn = page.locator("[role='tab']").first
            tab1_btn.click()
            time.sleep(1)
            
            # 9. Verify no severe console errors
            print(f"[9] Console errors captured: {len(console_errors)}")
            real_errors = [e for e in console_errors if "favicon" not in e.lower()]
            print(f"  -> Real console errors: {len(real_errors)}")
            if real_errors:
                print("  Errors:", real_errors)
            assert len(real_errors) == 0, f"Console errors found: {real_errors}"
            
            # Capture screenshots for report
            screenshot_dir = Path(tempfile.gettempdir()) / "daegu_qa_screenshots"
            screenshot_dir.mkdir(exist_ok=True)
            page.set_viewport_size({"width": 1920, "height": 1080})
            page.screenshot(path=str(screenshot_dir / "full_hero_view.png"), full_page=False)
            print(f"[*] Screenshot saved to {screenshot_dir / 'full_hero_view.png'}")
            
            browser.close()
            print("=" * 70)
            print("ALL BROWSER UI QA CHECKS PASSED! (100%)")
            print("=" * 70)
    finally:
        if proc:
            proc.terminate()

if __name__ == "__main__":
    run_browser_qa()
