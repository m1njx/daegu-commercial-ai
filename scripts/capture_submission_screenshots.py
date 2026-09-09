# -*- coding: utf-8 -*-
"""
scripts/capture_submission_screenshots.py

Phase 11: 공모전 제안서 제출용 고품질 스크린샷 캡처 스크립트
- Playwright Chromium 기반 고해상도(Retina 2x scale) 캡처
- 5개 핵심 스크린샷 원자적 자동 캡처
- 캡처 후 실제 데이터 및 수치 일치성 검증
"""

import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT_DIR / "submission" / "screenshots"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def capture_all():
    print("=" * 70)
    print("Phase 11: 공모전 제안서 제출용 고품질 스크린샷 캡처 시작")
    print(f"출력 경로: {OUTPUT_DIR}")
    print("=" * 70)

    url = "http://localhost:8505"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Device scale factor 2 for crisp Retina text rendering
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=2
        )
        page = context.new_page()

        print("[*] Navigating to Streamlit app at", url)
        page.goto(url, wait_until="networkidle", timeout=60000)
        time.sleep(3)

        # ----------------------------------------------------
        # 1. Screenshot A: 01_main_recommendation.png
        # 시나리오 1: 카페 + 2030 + 기본 균형형 + 통합 대중교통 모델
        # ----------------------------------------------------
        print("\n[1/5] Capturing Screenshot A (01_main_recommendation.png)...")
        # Ensure default scenario is active
        page.wait_for_selector(".top1-hero-card", state="visible")
        top1_text = page.locator(".top1-hero-card").inner_text()
        print("  Top 1 Text excerpt:", top1_text.split("\n")[:4])
        assert "신암4동" in top1_text, "신암4동 누락"
        assert "77.75" in top1_text, "77.75점 누락"

        # Scroll to top to capture Hero Banner + KPIs + Top 1 Card
        page.evaluate("window.scrollTo(0, 0)")
        time.sleep(1)

        # We capture the full viewport (1920x1080) which nicely frames Sidebar + Hero + Top 1
        img_a_path = OUTPUT_DIR / "01_main_recommendation.png"
        page.screenshot(path=str(img_a_path), full_page=False)
        print(f"  -> Saved {img_a_path} ({img_a_path.stat().st_size:,} bytes)")

        # ----------------------------------------------------
        # 2. Screenshot B: 02_transit_map.png
        # 시나리오 1 지도 + Top 5 + 대중교통 레이어
        # ----------------------------------------------------
        print("\n[2/5] Capturing Screenshot B (02_transit_map.png)...")
        # Locate the dashboard panel containing Top 5 cards and the map
        # Scroll to map area
        map_elem = page.locator(".compact-top-grid").locator("xpath=../..")
        map_elem.scroll_into_view_if_needed()
        time.sleep(2)

        img_b_path = OUTPUT_DIR / "02_transit_map.png"
        # Take screenshot of the map and Top 5 dashboard panel section
        # Let's frame the container nicely
        panel_container = page.locator("div[data-testid='stHorizontalBlock']").first
        if panel_container.is_visible():
            panel_container.screenshot(path=str(img_b_path))
        else:
            page.screenshot(path=str(img_b_path), full_page=False)
        print(f"  -> Saved {img_b_path} ({img_b_path.stat().st_size:,} bytes)")

        # ----------------------------------------------------
        # 3. Screenshot C: 03_explainable_analysis.png
        # 시나리오 4: 학원 + 10대 청소년층 + 타깃고객 집중형 -> 범어1동 84.47점
        # ----------------------------------------------------
        print("\n[3/5] Capturing Screenshot C (03_explainable_analysis.png)...")
        # Select Scenario 4 in sidebar dropdown
        demo_select = page.locator("div[data-testid='stSelectbox']").first
        demo_select.click()
        time.sleep(1)
        # Click scenario 4
        page.locator("li[role='option']", has_text="시나리오 4").click()
        time.sleep(3)
        page.wait_for_selector(".top1-hero-card", state="visible")

        top1_c_text = page.locator(".top1-hero-card").inner_text()
        print("  Scenario 4 Top 1:", top1_c_text.split("\n")[:4])
        assert "범어1동" in top1_c_text, f"범어1동 누락: {top1_c_text}"
        assert "84.47" in top1_c_text, f"84.47점 누락: {top1_c_text}"

        # Click Tab 2 (지도 보기 · 상세 분석)
        tab_btns = page.locator("button[role='tab']").all()
        tab2_btn = tab_btns[1] # Tab 2
        tab2_btn.click()
        time.sleep(3)

        # Frame the radar chart and component diagnosis
        page.evaluate("window.scrollTo(0, 350)")
        time.sleep(1)

        img_c_path = OUTPUT_DIR / "03_explainable_analysis.png"
        page.screenshot(path=str(img_c_path), full_page=False)
        print(f"  -> Saved {img_c_path} ({img_c_path.stat().st_size:,} bytes)")

        # ----------------------------------------------------
        # 4. Screenshot D: 04_model_comparison.png
        # 시나리오 2: 한식 + 전체 (배후수요형)
        # ----------------------------------------------------
        print("\n[4/5] Capturing Screenshot D (04_model_comparison.png)...")
        # Select Scenario 2 in sidebar dropdown
        demo_select = page.locator("div[data-testid='stSelectbox']").first
        demo_select.click()
        time.sleep(1)
        page.locator("li[role='option']", has_text="시나리오 2").click()
        time.sleep(3)

        # Click Tab 3 (Baseline vs 통합교통 모델)
        tab_btns = page.locator("button[role='tab']").all()
        tab3_btn = tab_btns[2] # Tab 3
        tab3_btn.click()
        time.sleep(2)

        page.evaluate("window.scrollTo(0, 300)")
        time.sleep(1)

        img_d_path = OUTPUT_DIR / "04_model_comparison.png"
        page.screenshot(path=str(img_d_path), full_page=False)
        print(f"  -> Saved {img_d_path} ({img_d_path.stat().st_size:,} bytes)")

        # ----------------------------------------------------
        # 5. Screenshot E: 05_financial_roadmap.png
        # Tab 4: iM뱅크 연계 로드맵
        # ----------------------------------------------------
        print("\n[5/5] Capturing Screenshot E (05_financial_roadmap.png)...")
        tab4_btn = tab_btns[3] # Tab 4
        tab4_btn.click()
        time.sleep(2)

        page.evaluate("window.scrollTo(0, 250)")
        time.sleep(1)

        img_e_path = OUTPUT_DIR / "05_financial_roadmap.png"
        page.screenshot(path=str(img_e_path), full_page=False)
        print(f"  -> Saved {img_e_path} ({img_e_path.stat().st_size:,} bytes)")

        browser.close()

    print("\n" + "=" * 70)
    print("ALL 5 SCREENSHOTS CAPTURED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    capture_all()
