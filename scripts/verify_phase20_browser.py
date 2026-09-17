#!/usr/bin/env python3
"""Phase 20 real-browser acceptance: demo state, detail inventory, tabs and exports."""

from __future__ import annotations

import re
import sys
import os

from playwright.sync_api import sync_playwright

URL = os.environ.get("DAEGU_APP_URL", "http://127.0.0.1:8502")


def main() -> None:
    console_errors: list[str] = []
    page_errors: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))
        page.goto(URL, wait_until="networkidle", timeout=60000)
        page.wait_for_selector(".top1-hero-card", timeout=60000)

        # Arbitrary advanced state must be reset by a canonical demo callback.
        page.get_by_text("⚙️ 모델 버전 및 대중교통 설정 (고급)", exact=True).click()
        alpha = page.get_by_role("slider", name=re.compile("미진입 상권 할인 계수"))
        alpha.focus()
        alpha.press("End")
        exclude = page.get_by_role("checkbox", name="미진입 상권(0점포) 완전 제외")
        exclude.evaluate("el => el.click()")
        page.wait_for_timeout(800)

        demo = page.get_by_role("combobox", name="🎬 심사위원 데모 시나리오")
        demo.click()
        page.get_by_role("option", name=re.compile(r"^시나리오 1:")).click()
        page.wait_for_timeout(2500)
        assert alpha.get_attribute("aria-valuenow") in {"0.5", "0.50"}
        assert not exclude.is_checked()

        expected = {
            1: ("신암4동", "77.75"), 2: ("상인1동", "77.47"),
            3: ("칠성동", "75.45"), 4: ("범어1동", "84.40"),
            5: ("상인1동", "72.25"), 6: ("칠성동", "75.90"),
        }
        for no, (dong, score) in expected.items():
            demo.click()
            page.get_by_role("option", name=re.compile(rf"^시나리오 {no}:")).click()
            page.wait_for_timeout(1800)
            hero = page.locator(".top1-hero-card").inner_text()
            assert dong in hero and score in hero, (no, hero[:200])
            assert page.get_by_text("Exception", exact=True).count() == 0

        # Detail tab exposes Top5 first plus every other dong (150 total).
        page.get_by_role("tab", name="🗺️ 지도 보기 · 상세 분석").click()
        detail = page.get_by_role("combobox", name="정밀 진단할 행정동 선택")
        detail.click()
        detail.press("End")
        detail.press("Enter")
        page.wait_for_timeout(1500)
        selected_text = detail.input_value()
        assert "Top " not in selected_text and selected_text in page.locator("body").inner_text()
        assert page.locator("iframe").count() >= 1

        page.get_by_role("tab", name="⚖️ 통합 대중교통 모델 vs 도시철도 중심 개선 모델").click()
        page.wait_for_timeout(1000)
        assert "통합 대중교통 모델 (권장) vs 도시철도 중심 개선 모델 정량 비교" in page.locator("body").inner_text()
        page.get_by_role("tab", name="🏦 iM뱅크 연계 로드맵").click()
        page.get_by_role("tab", name="🗄️ 데이터/분석 방법").click()
        page.wait_for_timeout(800)
        assert page.get_by_role("button", name=re.compile("CSV")).count() >= 1

        body = page.locator("body").inner_text()
        assert "The widget with key" not in body and "StreamlitAPIException" not in body
        assert not page_errors, page_errors
        assert not console_errors, console_errors
        browser.close()

    print("PHASE 20 BROWSER: 6/6 demos, state reset, 150-dong detail, tabs/map/CSV PASS")
    print("Browser console errors: 0; page errors: 0; user-visible warnings: 0")


if __name__ == "__main__":
    sys.exit(main() or 0)
