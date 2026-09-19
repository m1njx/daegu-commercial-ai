#!/usr/bin/env python3
"""Build the five-page final proposal summary from Phase 22 source-of-truth values."""

from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, KeepTogether,
)

import os

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "submission/documents/제안 요약서.pdf"
SHOTS = ROOT / "screenshots" if (ROOT / "screenshots").is_dir() else ROOT / "submission/screenshots"

def find_korean_font() -> str:
    """Find a valid Korean font across OS environments (macOS, Linux, Windows) or environment variable."""
    env_font = os.environ.get("KOREAN_FONT_PATH")
    if env_font and Path(env_font).is_file():
        return env_font
        
    candidates = [
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/Library/Fonts/NanumGothic.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/nanum/NanumGothic.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "C:\\Windows\\Fonts\\malgun.ttf",
        "C:\\Windows\\Fonts\\gulim.ttc",
    ]
    for c in candidates:
        if Path(c).is_file():
            return c
    raise FileNotFoundError(
        "사용 가능한 한국어 TTF 폰트를 시스템에서 찾을 수 없습니다. "
        "KOREAN_FONT_PATH 환경 변수로 폰트 경로를 지정해 주세요."
    )

FONT = find_korean_font()
pdfmetrics.registerFont(TTFont("Korean", FONT))

PAGE_W, PAGE_H = A4
MARGIN_X = 18 * mm
TOP = 18 * mm
BOTTOM = 15 * mm


def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Korean", 8)
    canvas.setFillColor(colors.HexColor("#64748B"))
    canvas.drawString(MARGIN_X, 8 * mm, "말괄량이코물이 | 2026 AI Blockchain Challenge in Daegu")
    canvas.drawRightString(PAGE_W - MARGIN_X, 8 * mm, f"{doc.page} / 5")
    canvas.restoreState()


def scaled_image(path, max_w, max_h):
    img = Image(str(path))
    ratio = min(max_w / img.imageWidth, max_h / img.imageHeight)
    img.drawWidth = img.imageWidth * ratio
    img.drawHeight = img.imageHeight * ratio
    return img


def build():
    styles = getSampleStyleSheet()
    body = ParagraphStyle("BodyK", parent=styles["BodyText"], fontName="Korean", fontSize=9.3,
                          leading=14, textColor=colors.HexColor("#1F2937"), spaceAfter=5)
    small = ParagraphStyle("SmallK", parent=body, fontSize=8.2, leading=11.5, textColor=colors.HexColor("#475569"))
    title = ParagraphStyle("TitleK", parent=body, fontSize=18, leading=23, alignment=TA_CENTER,
                           textColor=colors.HexColor("#0F3D75"), spaceAfter=10)
    h1 = ParagraphStyle("H1K", parent=body, fontSize=12.5, leading=16, textColor=colors.HexColor("#0F3D75"),
                        spaceBefore=7, spaceAfter=5)
    h2 = ParagraphStyle("H2K", parent=body, fontSize=10.5, leading=14, textColor=colors.HexColor("#0F172A"),
                        spaceBefore=5, spaceAfter=3)
    caption = ParagraphStyle("CaptionK", parent=small, alignment=TA_CENTER, fontSize=8, leading=11,
                             textColor=colors.HexColor("#334155"), spaceBefore=3, spaceAfter=8)
    note = ParagraphStyle("NoteK", parent=small, backColor=colors.HexColor("#EFF6FF"), borderColor=colors.HexColor("#BFDBFE"),
                          borderWidth=0.6, borderPadding=6, spaceBefore=5, spaceAfter=7)

    doc = BaseDocTemplate(str(OUT), pagesize=A4, leftMargin=MARGIN_X, rightMargin=MARGIN_X,
                          topMargin=TOP, bottomMargin=BOTTOM, title="제안 요약서")
    frame = Frame(MARGIN_X, BOTTOM, PAGE_W - 2 * MARGIN_X, PAGE_H - TOP - BOTTOM, id="normal")
    doc.addPageTemplates(PageTemplate(id="main", frames=[frame], onPage=header_footer))
    story = []

    story += [Paragraph("붙임 4 · 제안 요약서 (A4 5장)", small),
              Paragraph("대구 소상공인 AI 상권·창업 입지 추천 서비스", title)]
    info = Table([["접수번호", "", "팀명", "말괄량이코물이"],
                  ["공모전", "2026 AI Blockchain Challenge in Daegu", "분야", "소상공인·골목상권 디지털 금융"]],
                 colWidths=[23*mm, 72*mm, 18*mm, 46*mm])
    info.setStyle(TableStyle([("FONTNAME",(0,0),(-1,-1),"Korean"),("FONTSIZE",(0,0),(-1,-1),8.5),
                              ("GRID",(0,0),(-1,-1),0.5,colors.HexColor("#94A3B8")),
                              ("BACKGROUND",(0,0),(0,-1),colors.HexColor("#EFF6FF")),
                              ("BACKGROUND",(2,0),(2,-1),colors.HexColor("#EFF6FF")),
                              ("VALIGN",(0,0),(-1,-1),"MIDDLE"),("ALIGN",(0,0),(-1,-1),"CENTER"),
                              ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)]))
    story += [info, Paragraph("1. 제안 목적과 필요성", h1),
              Paragraph("예비 창업자는 수요·타깃 인구·경쟁·교통·주차·업종 분포를 서로 다른 기관에서 찾아 비교해야 합니다. 본 서비스는 대구 150개 행정동을 같은 기준으로 정규화하여 후보지를 비교하고, 점수 근거와 주의사항을 함께 제시합니다.", body),
              Paragraph("2. 핵심 해결책", h1),
              Paragraph("공공데이터 기반 MCDM(다기준 의사결정) 방식의 상대적 입지 적합도 순위 모델입니다. 사용자가 업종·타깃·전략 가중치를 선택하면 6개 컴포넌트를 0~100점으로 환산해 Top 5와 150개 전체 결과를 제공합니다.", body)]
    comp = Table([["컴포넌트","기본 가중치","핵심 입력"],
                  ["배후수요","30%","인구·밀도·도시철도 승하차·총점포"],
                  ["타깃적합","20%","선택 연령층 비중·절대 인구"],
                  ["경쟁","15%","점포당 타깃인구·선택 업종 300m 경쟁"],
                  ["대중교통","15%","도시철도 70% + 시내버스 30%"],
                  ["주차","10%","부설주차장 공급 Proxy"],
                  ["업종특화","10%","LQ 백분위"]], colWidths=[35*mm,25*mm,99*mm])
    comp.setStyle(TableStyle([("FONTNAME",(0,0),(-1,-1),"Korean"),("FONTSIZE",(0,0),(-1,-1),8.2),
                              ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#DBEAFE")),
                              ("GRID",(0,0),(-1,-1),0.35,colors.HexColor("#CBD5E1")),
                              ("VALIGN",(0,0),(-1,-1),"MIDDLE"),("ALIGN",(1,1),(1,-1),"CENTER"),
                              ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4)]))
    story += [comp, Paragraph("3. 데이터와 기술", h1),
              Paragraph("상가상권정보 118,357개, 주민등록 인구 약 234.7만 명, 도시철도 94개 역, 시내버스 정류소 3,981개소, 부설주차장 247,329면을 행정동·공간좌표 기준으로 결합합니다.", body),
              Paragraph("Python · Pandas · NumPy · SciPy · GeoPandas · Shapely · PyProj · PyArrow · Folium · Streamlit · Playwright", note),
              Paragraph("도시철도와 버스의 승하차는 관측·집계 이용량이며 통신사 유동인구가 아닙니다. 주차는 이용량이 아닌 공급 여건 Proxy입니다.", small), PageBreak()]

    story += [Paragraph("4. 모델 정의와 검증", h1),
              Paragraph("경쟁점포 범위", h2),
              Paragraph("사용자가 선택한 업종 집합과 경쟁점포 모집단을 일치시켰습니다. 음식점은 음식 대분류 전체, 학원은 일반·기타 교육 결합, 단일 업종은 해당 중분류를 대상으로 각 점포 반경 300m의 다른 선택 업종 점포 수를 계산합니다.", body),
              Paragraph("업종특화와 점포 미확인 지역", h2),
              Paragraph("Industry Fit은 중복 정보를 제거해 LQ 백분위만 사용합니다. 해당 업종 점포가 확인되지 않는 지역은 경쟁점수에 현재 할인계수 α를 적용하며 기본값은 0.50입니다. 이 상태는 수요가 입증됐다는 뜻이 아닙니다.", body)]
    demos = [["데모","프리셋","Top 1","점수"],
             ["카페 + 2030","기본 균형형","신암4동","77.75"],
             ["한식 + 전체","배후 수요 집중형","상인1동","77.47"],
             ["미용실 + 2030","기본 균형형","칠성동","75.45"],
             ["학원 + 10대 이하","타깃 고객 집중형","범어1동","84.40"],
             ["종합소매 + 전체","기본 균형형","상인1동","72.25"],
             ["숙박 + 2030","기본 균형형","칠성동","75.90"]]
    table = Table(demos, colWidths=[39*mm,58*mm,37*mm,25*mm])
    table.setStyle(TableStyle([("FONTNAME",(0,0),(-1,-1),"Korean"),("FONTSIZE",(0,0),(-1,-1),8.1),
                               ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#DBEAFE")),
                               ("GRID",(0,0),(-1,-1),0.35,colors.HexColor("#CBD5E1")),
                               ("ALIGN",(2,1),(-1,-1),"CENTER"),("TOPPADDING",(0,0),(-1,-1),4),
                               ("BOTTOMPADDING",(0,0),(-1,-1),4)]))
    story += [Paragraph("최종 공식 데모 결과", h2), table,
              Paragraph("모델 비교와 테스트 해석", h2),
              Paragraph("도시철도 중심 개선 모델과 통합 대중교통 모델의 6개 데모 Spearman 범위는 0.9915~0.9969입니다. 이는 두 모델의 전체 행정동 순위가 유사하다는 뜻이며 사업적 정확도나 창업 성공 가능성을 의미하지 않습니다.", body),
              Paragraph("17개 스위트 213/213 PASS. 자동화 테스트는 코드 실행, 데이터 무결성, 계산 재현성 및 UI·문서 정합성을 검증하며 실제 창업 성과, 매출, 생존율 또는 사업적 유효성을 검증하지 않습니다.", note),
              Paragraph("5. 한계와 구현 범위", h1),
              Paragraph("실제 매출·폐업·생존 ground truth, 임대료·권리금·실시간 공실률은 포함하지 않습니다. 행정동 단위 후보지 비교 후 현장 수요·비용·인허가를 별도로 확인해야 합니다. 현재 구현은 AI 입지 추천 중심이며 금융 로드맵 2~4단계는 향후 확장 계획입니다.", body), PageBreak()]

    story += [Paragraph("6. 기대효과와 서비스 화면", h1),
              Paragraph("소상공인은 흩어진 공공데이터를 한 화면에서 같은 기준으로 비교하고, 단일 추천 순위뿐 아니라 컴포넌트 점수·관측 수치·주의사항을 함께 확인할 수 있습니다. 지역 금융기관은 상담 초기 후보지 비교 자료로 활용할 수 있습니다.", body),
              Paragraph("화면 1. 메인 추천 결과 - 현재 조건, Top 5, 상대적 점수와 지도", h2),
              scaled_image(SHOTS/"01_main_recommendation.png", 159*mm, 104*mm),
              Paragraph("카페+2030 기본 균형형 예시. 신암4동 77.75점이며 점수는 150개 행정동 사이의 상대적 입지 적합도입니다.", caption),
              Paragraph("화면 표기 원칙", h2),
              Paragraph("‘해당 업종 점포 확인 지역 / 점포 미확인 지역’처럼 관측 사실을 중립적으로 표시합니다. 점포 존재를 사업성 검증으로 해석하지 않으며 LQ가 1 이상일 때만 대구 평균 대비 업종 비중 우위를 설명합니다.", body),
              Paragraph("사용 흐름", h2),
              Paragraph("① 업종·타깃 선택 → ② 전략 프리셋 또는 직접 가중치 조정 → ③ 150개 행정동 점수 산출 → ④ Top 5·지도 확인 → ⑤ 상세 컴포넌트와 관측 지표 검토 → ⑥ CSV 저장 및 현장 검토", body),
              Paragraph("기대효과", h2),
              Paragraph("후보지 비교 기준을 일관되게 만들고, 추천 결과와 함께 근거·한계를 표시해 상담 과정의 탐색 시간을 줄입니다. 공개 데이터와 결정론적 계산을 사용하므로 같은 입력에서 결과를 재현할 수 있습니다.", body), PageBreak()]

    story += [Paragraph("7. 서비스 화면 - 지도와 상세 분석", h1),
              Paragraph("화면 2. Top 5 추천 지역과 대구 상권 지도", h2),
              scaled_image(SHOTS/"02_transit_map.png", 159*mm, 87*mm),
              Paragraph("행정동별 상대 점수 분포, Top 5 위치와 도시철도 레이어를 동시에 확인합니다.", caption),
              Paragraph("화면 3. 설명 가능한 상세 분석", h2),
              scaled_image(SHOTS/"03_explainable_analysis.png", 159*mm, 87*mm),
              Paragraph("학원+10대 이하 타깃 예시. 범어1동 84.40점과 6개 컴포넌트, 실제 관측·집계 지표 및 확인 필요사항을 제시합니다.", caption), PageBreak()]

    story += [Paragraph("8. 서비스 화면 - 모델 비교와 확장 로드맵", h1),
              Paragraph("화면 4. 동일 α 조건의 교통 접근성 모델 비교", h2),
              scaled_image(SHOTS/"04_model_comparison.png", 159*mm, 87*mm),
              Paragraph("통합 대중교통 모델과 도시철도 중심 개선 모델을 같은 α에서 비교합니다. 할인 적용 전후 비교가 아닙니다.", caption),
              Paragraph("화면 5. iM뱅크 금융 연계 로드맵", h2),
              scaled_image(SHOTS/"05_financial_roadmap.png", 159*mm, 87*mm),
              Paragraph("현재 제공 범위는 1단계 입지 추천입니다. 금융상담·정책자금·API 연계는 사용자 동의와 제휴를 전제로 한 향후 확장 범위입니다.", caption)]

    doc.build(story)
    print(OUT)


if __name__ == "__main__":
    build()
