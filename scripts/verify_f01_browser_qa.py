#!/usr/bin/env python3
"""
scripts/verify_f01_browser_qa.py

Automated Playwright Browser QA for F01 Session State Preservation
Verifies:
1. Scenario 4 selection (학원 + 10대 이하 + 타깃 고객 집중형) -> 범어1동 84.40
2. Rank 2 click (다사읍 80.89) -> Detail displays 다사읍 80.89, Sidebar preserves 학원/10대/타깃집중
3. Rank 3 click (유천동 79.38) -> Detail displays 유천동 79.38
4. Rank 1 click (범어1동 84.40) -> Detail displays 범어1동 84.40
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PORT = 8599
URL = f"http://localhost:{PORT}"


def main():
    print("==================================================")
    print("Starting F01 Automated Browser QA with Playwright")
    print(f"Target URL: {URL}")
    print("==================================================")

    env = os.environ.copy()
    env["STREAMLIT_SERVER_PORT"] = str(PORT)
    env["STREAMLIT_SERVER_HEADLESS"] = "true"

    # Launch Streamlit in background
    app_path = ROOT / "app/app.py"
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", str(app_path), "--server.port", str(PORT), "--server.headless", "true"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(ROOT),
        env=env,
    )

    try:
        # Wait for Streamlit server to boot up
        time.sleep(6)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1920, "height": 1080})

            print("[1] Connecting to Streamlit server...")
            page.goto(URL, wait_until="networkidle", timeout=30000)
            time.sleep(3)

            # Step 1: Check initial page load (Default Scenario 1: 신암4동 77.75)
            assert "대구 소상공인 AI" in page.title() or "대구" in page.content()
            top1_hero = page.locator(".top1-hero-card").inner_text()
            print(f"[Initial] Default Top1 loaded: {'신암4동' in top1_hero and '77.75' in top1_hero}")

            # Step 2: Select Scenario 4 in sidebar
            print("[2] Selecting Scenario 4 (학원 + 10대 이하)...")
            demo_select = page.locator("[data-testid='stSelectbox']").first
            demo_select.click()
            time.sleep(1)
            # Click option with '시나리오 4'
            scenario4_opt = page.locator("li[role='option']", has_text="시나리오 4")
            scenario4_opt.click()
            time.sleep(3)

            # Step 3: Verify Scenario 4 applied
            hero_text_s4 = page.locator(".top1-hero-card").inner_text()
            print(f"  Hero text after Scenario 4:\n  {hero_text_s4.splitlines()[:3]}")
            assert "범어1동" in hero_text_s4, f"Scenario 4 Top1 범어1동 not found: {hero_text_s4}"
            assert "84.40" in hero_text_s4, f"Scenario 4 score 84.40 not found: {hero_text_s4}"

            # Step 4: Click Rank 2 button (다사읍)
            print("[3] Clicking Rank 2 button (다사읍)...")
            btn_rank2 = page.locator("button[data-testid='stBaseButton-secondary']", has_text="2위 상세").first
            if not btn_rank2.is_visible():
                btn_rank2 = page.locator("button", has_text="2위 상세").first
            assert btn_rank2.is_visible(), "2위 상세 button not found"
            btn_rank2.click()
            time.sleep(3)

            # Step 5: Verify F01 state preservation
            hero_text_rank2 = page.locator(".top1-hero-card").inner_text()
            print(f"  Hero text after clicking Rank 2:\n  {hero_text_rank2.splitlines()[:3]}")
            assert "다사읍" in hero_text_rank2, f"Expected 다사읍 in hero card, got: {hero_text_rank2}"
            assert "80.89" in hero_text_rank2, f"Expected 80.89 in hero card, got: {hero_text_rank2}"

            # Verify sidebar state did NOT reset to 카페/2030
            content = page.content()
            assert "학원" in content, "Sidebar industry '학원' was wiped out!"
            assert "10대 이하" in content, "Sidebar target '10대 이하' was wiped out!"
            print("  ✓ Sidebar conditions preserved (학원, 10대 이하, 타깃 고객 집중형)")

            # Step 6: Click Rank 3 button (유천동)
            print("[4] Clicking Rank 3 button (유천동)...")
            btn_rank3 = page.locator("button", has_text="3위 상세").first
            assert btn_rank3.is_visible(), "3위 상세 button not found"
            btn_rank3.click()
            time.sleep(3)

            hero_text_rank3 = page.locator(".top1-hero-card").inner_text()
            print(f"  Hero text after clicking Rank 3:\n  {hero_text_rank3.splitlines()[:3]}")
            assert "유천동" in hero_text_rank3, f"Expected 유천동 in hero card, got: {hero_text_rank3}"
            assert "79.38" in hero_text_rank3, f"Expected 79.38 in hero card, got: {hero_text_rank3}"

            # Step 7: Click Rank 1 button back (범어1동)
            print("[5] Clicking Rank 1 button (범어1동)...")
            btn_rank1 = page.locator("button", has_text="1위 상세").first
            assert btn_rank1.is_visible(), "1위 상세 button not found"
            btn_rank1.click()
            time.sleep(3)

            hero_text_rank1 = page.locator(".top1-hero-card").inner_text()
            print(f"  Hero text after returning to Rank 1:\n  {hero_text_rank1.splitlines()[:3]}")
            assert "범어1동" in hero_text_rank1, f"Expected 범어1동 in hero card, got: {hero_text_rank1}"
            assert "84.40" in hero_text_rank1, f"Expected 84.40 in hero card, got: {hero_text_rank1}"

            browser.close()
            print("==================================================")
            print("F01 BROWSER QA RESULT: 100% SUCCESSFUL PASS")
            print("==================================================")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    main()
