#!/usr/bin/env python3
"""Phase 21 real-Chromium acceptance, including downloaded CSV bytes."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = os.environ.get("DAEGU_APP_URL", "http://127.0.0.1:8502")
MODELS = (
    "통합 대중교통 모델 (권장 / 도시철도 70% + 시내버스 30%)",
    "도시철도 중심 모델 (도시철도 역세권 중심)",
    "초기 기준선 모델 (도시철도 단순 거리)",
)
DEMOS = {
    1: ("신암4동", "77.75"), 2: ("상인1동", "77.47"),
    3: ("칠성동", "75.45"), 4: ("범어1동", "84.40"),
    5: ("상인1동", "72.25"), 6: ("칠성동", "75.90"),
}
BAD_VISIBLE = (
    "Traceback", "KeyError", "StreamlitAPIException", "The widget with key",
    "비중가", "인원가", "여건가", "미크로", "2026 iM뱅크 데이터톤",
    "학원가 LQ 2.37", "감삼동 1위 / 0점포 왜곡 방어 실증",
)


def main() -> None:
    console_errors: list[str] = []
    page_errors: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080}, accept_downloads=True)
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.goto(URL, wait_until="networkidle", timeout=60_000)
        page.wait_for_selector(".top1-hero-card", timeout=60_000)

        demo = page.get_by_role("combobox", name="🎬 심사위원 데모 시나리오")
        for number, (dong, score) in DEMOS.items():
            demo.click()
            page.get_by_role("option", name=re.compile(rf"^시나리오 {number}:")).click()
            page.wait_for_timeout(1_300)
            body = page.locator("body").inner_text()
            assert dong in body and score in body, (number, dong, score)
            assert not any(bad in body for bad in BAD_VISIBLE), number
            assert page.locator(".compact-rank-card").count() == 5

        # The two corrected demo labels are the actual selector values.
        demo.click()
        page.get_by_role("option", name=re.compile(r"^시나리오 4:")).click()
        page.wait_for_timeout(600)
        assert page.get_by_text(re.compile(r"^시나리오 4:.*학원 특화도 LQ 1\.90")).count() >= 1
        demo.click()
        page.get_by_role("option", name=re.compile(r"^시나리오 6:")).click()
        page.wait_for_timeout(1_000)
        assert page.get_by_text(re.compile(r"^시나리오 6:.*점포 미확인 지역 보정 비교")).count() >= 1

        # Demo reset and filtered count: lodging excludes exactly 23 of 150 dongs.
        page.get_by_text("⚙️ 모델 버전 및 대중교통 설정 (고급)", exact=True).click()
        alpha = page.get_by_role("slider", name=re.compile("미진입 상권 할인 계수"))
        assert alpha.get_attribute("aria-valuenow") in {"0.5", "0.50"}
        exclude = page.get_by_role("checkbox", name="미진입 상권(0점포) 완전 제외")
        assert not exclude.is_checked()
        exclude.evaluate("element => element.click()")
        page.wait_for_timeout(1_000)
        page.get_by_role("tab", name="🗄️ 데이터/분석 방법").click()
        page.wait_for_timeout(600)
        body = page.locator("body").inner_text()
        assert "현재 조건 랭킹 데이터 127개 (전체 150개 중" in body
        assert "현재 조건 127개 행정동 추천 데이터 CSV 다운로드" in body

        # All three model exports are real UTF-8-SIG byte downloads.
        with tempfile.TemporaryDirectory() as temp_dir:
            for model in MODELS:
                current_exclude = page.get_by_role("checkbox", name="미진입 상권(0점포) 완전 제외")
                if current_exclude.count() == 0:
                    page.get_by_text("⚙️ 모델 버전 및 대중교통 설정 (고급)", exact=True).click()
                page.get_by_text(model, exact=True).click()
                page.wait_for_timeout(700)
                current_exclude = page.get_by_role("checkbox", name="미진입 상권(0점포) 완전 제외")
                if current_exclude.is_checked():
                    current_exclude.evaluate("element => element.click()")
                    page.wait_for_timeout(700)
                page.get_by_role("tab", name="🗄️ 데이터/분석 방법").click()
                button = page.get_by_role("button", name="📥 현재 조건 150개 행정동 추천 데이터 CSV 다운로드")
                with page.expect_download(timeout=15_000) as event:
                    button.click()
                path = Path(temp_dir) / f"{len(list(Path(temp_dir).iterdir()))}.csv"
                event.value.save_as(path)
                data = path.read_bytes()
                assert data[:3] == b"\xef\xbb\xbf"
                decoded = data.decode("utf-8-sig")
                assert "행정동명" in decoded and "신암4동" in decoded

        # Detail, comparison, map, and period wording remain live.
        page.get_by_role("tab", name="🗺️ 지도 보기 · 상세 분석").click()
        detail = page.get_by_role("combobox", name="정밀 진단할 행정동 선택")
        detail.click(); detail.press("End"); detail.press("Enter")
        page.wait_for_timeout(600)
        body = page.locator("body").inner_text()
        assert "도시철도는 2026년 1~7월 일별 관측(212일)" in body
        assert "시내버스는 같은 기간의 월별 집계를 212일로 나눈 일평균" in body
        assert page.locator("iframe").count() >= 1
        page.get_by_role("tab", name="⚖️ 통합 대중교통 모델 vs 도시철도 중심 개선 모델").click()
        page.wait_for_timeout(500)
        body = page.locator("body").inner_text()
        assert "높은 순위 유사도" in body or "일부 순위 변화" in body or "순위 변화 확인 필요" in body
        assert not any(bad in body for bad in BAD_VISIBLE)
        assert not page_errors, page_errors
        assert not console_errors, console_errors
        browser.close()

    print("PHASE 21 BROWSER: 6 demos, 3 models, Tab2/3/5, filtered count, map PASS")
    print("CSV downloads: 3/3 UTF-8-SIG BOM PASS")
    print("Browser console errors: 0; page errors: 0; user-visible warnings: 0")


if __name__ == "__main__":
    main()
