#!/usr/bin/env python3
"""Phase 22 real Chromium acceptance for demos, alpha semantics, tabs and CSV."""

from pathlib import Path
import os
import re
import tempfile

from playwright.sync_api import sync_playwright

URL = os.environ.get("DAEGU_APP_URL", "http://127.0.0.1:8502")
DEMOS = {1:("신암4동","77.75"),2:("상인1동","77.47"),3:("칠성동","75.45"),4:("범어1동","84.40"),5:("상인1동","72.25"),6:("칠성동","75.90")}
MODELS = (
    "통합 대중교통 모델 (권장 / 도시철도 70% + 시내버스 30%)",
    "도시철도 중심 모델 (도시철도 역세권 중심)",
    "초기 기준선 모델 (도시철도 단순 거리)",
)


def slider_value(locator) -> float:
    """Read both legacy Streamlit aria-valuenow and current range input."""
    value = locator.get_attribute("aria-valuenow")
    return float(value if value is not None else locator.input_value())


def main() -> None:
    console_errors, page_errors = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        viewport = {
            "width": int(os.environ.get("VIEWPORT_WIDTH", "1920")),
            "height": int(os.environ.get("VIEWPORT_HEIGHT", "1080")),
        }
        page = browser.new_page(viewport=viewport, accept_downloads=True)
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: page_errors.append(str(e)))
        page.goto(URL, wait_until="networkidle", timeout=60_000)
        page.wait_for_selector(".top1-hero-card", timeout=60_000)
        demo = page.get_by_role("combobox", name="🎬 심사위원 데모 시나리오")
        for no, (dong, score) in DEMOS.items():
            demo.click(); page.get_by_role("option", name=re.compile(rf"^시나리오 {no}:")).click()
            page.wait_for_timeout(1_200)
            hero = page.locator(".top1-hero-card").inner_text()
            assert dong in hero and score in hero, (no, hero[:200])

        page.get_by_text("⚙️ 모델 버전 및 대중교통 설정 (고급)", exact=True).click()
        for value, expected in ((0.30,"0.30"),(0.50,"0.50"),(0.80,"0.80")):
            alpha = page.get_by_role("slider", name=re.compile("점포 미확인 지역 할인 계수"))
            if alpha.count() == 0:
                page.get_by_text("⚙️ 모델 버전 및 대중교통 설정 (고급)", exact=True).click()
                alpha = page.get_by_role("slider", name=re.compile("점포 미확인 지역 할인 계수"))
            for _ in range(12):
                alpha = page.get_by_role("slider", name=re.compile("점포 미확인 지역 할인 계수"))
                current = slider_value(alpha)
                if abs(current - value) < 0.01:
                    break
                alpha.focus(); alpha.press("ArrowRight" if current < value else "ArrowLeft")
                page.wait_for_timeout(350)
            assert abs(slider_value(page.get_by_role("slider", name=re.compile("점포 미확인 지역 할인 계수"))) - value) < 0.01
            page.get_by_role("tab", name="⚖️ 통합 대중교통 모델 vs 도시철도 중심 개선 모델").click()
            body = page.locator("body").inner_text()
            assert f"현재 α={expected}" in body, (value, body[-2000:])
            assert "할인 적용 전후 비교표가 아닙니다" in body

        for model in MODELS:
            page.get_by_text(model, exact=True).click(); page.wait_for_timeout(900)
            assert page.locator(".top1-hero-card").count() == 1

        for tab in ("🏆 추천 결과", "🗺️ 지도 보기 · 상세 분석", "⚖️ 통합 대중교통 모델 vs 도시철도 중심 개선 모델", "🏦 iM뱅크 연계 로드맵", "🗄️ 데이터/분석 방법"):
            page.get_by_role("tab", name=tab).click(); page.wait_for_timeout(400)

        # Return to integrated mode and verify an actual UTF-8-SIG browser download.
        page.get_by_text(MODELS[0], exact=True).click(); page.wait_for_timeout(800)
        page.get_by_role("tab", name="🗄️ 데이터/분석 방법").click()
        button = page.get_by_role("button", name=re.compile("CSV 다운로드"))
        with tempfile.TemporaryDirectory() as temp:
            with page.expect_download(timeout=15_000) as event:
                button.click()
            path = Path(temp) / "result.csv"; event.value.save_as(path)
            assert path.read_bytes()[:3] == b"\xef\xbb\xbf"

        body = page.locator("body").inner_text()
        for stale in ("검증된 상권", "미검증 소규모 상권", "미포화 성장 기회", "StreamlitAPIException", "Traceback"):
            assert stale not in body
        assert not console_errors, console_errors
        assert not page_errors, page_errors
        browser.close()
    print("PHASE 22 BROWSER: 6 demos, 3 models, alpha 0.30/0.50/0.80, five tabs PASS")
    print("CSV UTF-8-SIG PASS; console errors 0; page errors 0; stale user claims 0")


if __name__ == "__main__":
    main()
