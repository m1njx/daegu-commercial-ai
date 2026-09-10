# -*- coding: utf-8 -*-
"""Real Chromium acceptance test for all six Phase 16 demo scenarios."""

from __future__ import annotations

import os
import re

from playwright.sync_api import sync_playwright

EXPECTED = [
    ("시나리오 1:", "카페", "2030", "신암4동", "77.75점"),
    ("시나리오 2:", "한식", "전체", "상인1동", "77.47점"),
    ("시나리오 3:", "미용실", "2030", "칠성동", "75.45점"),
    ("시나리오 4:", "학원", "10대", "범어1동", "84.47점"),
    ("시나리오 5:", "종합소매", "전체", "상인1동", "72.22점"),
    ("시나리오 6:", "숙박", "2030", "감삼동", "75.82점"),
]
BAD_VISIBLE = (
    "Traceback", "KeyError", "Uncaught app exception", "StreamlitAPIException",
    "created with a default value", "Session State API",
    "비중가", "인원가", "여건가", "미크로", "교통/유동인구 우선형",
)


def main():
    url = os.environ.get("DAEGU_APP_URL", "http://localhost:8502")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda error: console_errors.append(str(error)))
        results = []

        for prefix, industry, target, dong, score in EXPECTED:
            page.goto(url, wait_until="networkidle", timeout=45_000)
            demo = page.get_by_role("combobox", name="🎬 심사위원 데모 시나리오")
            demo.click()
            page.get_by_role("option", name=re.compile(rf"^{re.escape(prefix)}")).click()
            page.wait_for_timeout(1_500)
            body = page.locator("body").inner_text()
            for bad in BAD_VISIBLE:
                assert bad not in body, (prefix, bad)
            assert industry in body and target in body and dong in body and score in body
            assert page.locator(".compact-rank-card").count() == 5
            assert page.locator("iframe").first.is_visible()
            assert "추천 결과 종합" in body
            results.append((prefix, dong, score))

        # Every visible industry, target and preset selector option must rerun safely.
        page.goto(url, wait_until="networkidle", timeout=45_000)
        selectors = [
            ("희망 업종 선택", ["카페", "한식", "미용실", "학원", "종합소매", "숙박", "예술·스포츠", "직접 입력"]),
            ("타깃 고객층 선택", ["2030 청년 소비층 (20~39세)", "전체 인구 (전연령)", "10대 이하 (0~19세)", "4050 중장년 구매력층 (40~59세)", "60대 이상 시니어층"]),
            ("가중치 성향 프리셋", ["기본 균형형", "배후 수요 집중형 (대형 매장/안정형)", "타깃 고객 집중형 (트렌디/특화 소비)", "대중교통 접근성 우선형 (도보 테이크아웃)", "경쟁 회피 (블루오션 개척형)", "주차/차량 방문 중심형 (외곽/대형 식당)", "사용자 직접 조정"]),
        ]
        for label, options in selectors:
            for option in options:
                page.get_by_role("combobox", name=label).click()
                page.get_by_role("option", name=option, exact=True).click()
                page.wait_for_timeout(250)
                body = page.locator("body").inner_text()
                assert not any(bad in body for bad in BAD_VISIBLE), (label, option)

        # Reset, all model branches, exclusion filter, all tabs and download.
        page.get_by_role("button", name="가중치 초기화").click()
        page.get_by_text("⚙️ 모델 버전 및 대중교통 설정 (고급)", exact=True).click()
        for model in (
            "통합 대중교통 모델 (권장 / 도시철도 70% + 시내버스 30%)",
            "도시철도 중심 모델 (도시철도 역세권 중심)",
            "초기 기준선 모델 (도시철도 단순 거리)",
        ):
            page.get_by_text(model, exact=True).click()
            page.wait_for_timeout(500)
            checkbox_label = page.get_by_text("미진입 상권(0점포) 완전 제외", exact=True).last
            checkbox_label.click(force=True)
            page.wait_for_timeout(500)
            body = page.locator("body").inner_text()
            assert not any(bad in body for bad in BAD_VISIBLE), model
            checkbox_label = page.get_by_text("미진입 상권(0점포) 완전 제외", exact=True).last
            checkbox_label.click(force=True)

        tab_names = ("🏆 추천 결과", "🗺️ 지도 보기 · 상세 분석", "⚖️ 통합 대중교통 모델 vs 도시철도 중심 개선 모델", "🏦 iM뱅크 연계 로드맵", "🗄️ 데이터/분석 방법")
        for index, tab_name in enumerate(tab_names):
            page.locator("[role='tab']").nth(index).click()
            page.wait_for_timeout(700)
            assert tab_name in page.locator("body").inner_text()
            assert not any(bad in page.locator("body").inner_text() for bad in BAD_VISIBLE)
        search = page.get_by_role("textbox", name="행정동 검색 (예: 신암4동, 감삼동, 범어1동, 진천동)")
        search.wait_for(state="visible", timeout=10_000)
        search.fill("감삼")
        search.press("Enter")
        assert page.get_by_text(re.compile("감삼동")).count() > 0
        with page.expect_download(timeout=10_000) as download_info:
            page.get_by_role("button", name="📥 현재 조건 150개 행정동 추천 데이터 CSV 다운로드").click()
        assert download_info.value.suggested_filename.endswith(".csv")

        assert not console_errors, console_errors
        browser.close()
    for result in results:
        print("[PASS]", *result)
    print("PHASE 16 BROWSER: 6/6 demos + full control audit PASS; warning/error 0")


if __name__ == "__main__":
    main()
