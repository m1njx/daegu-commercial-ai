#!/usr/bin/env python3
"""
대구 소상공인시장진흥공단 상가(상권)정보 API 자동 수집 스크립트
공식 데이터셋: 소상공인시장진흥공단_상가(상권)정보_API (공공데이터포털)
Endpoint: https://apis.data.go.kr/B553077/api/open/sdsc2/storeListInDong
"""

import os
import sys
import time
import math
import json
import requests
import pandas as pd
from datetime import datetime
from urllib.parse import quote
from pathlib import Path

API_URL = "https://apis.data.go.kr/B553077/api/open/sdsc2/storeListInDong"
ROOT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT_DIR / "data/raw/commercial/소상공인시장진흥공단_상가상권정보"
OUTPUT_FILE = RAW_DIR / "소상공인시장진흥공단_상가업소정보_대구_20260907.csv"
METADATA_FILE = RAW_DIR / "collection_metadata.json"

def safe_request_error(exc: Exception, api_key: str) -> str:
    """Return an error message without exposing credentials embedded in URLs."""
    message = str(exc)
    for secret in (api_key, quote(api_key, safe="")):
        if secret:
            message = message.replace(secret, "[REDACTED]")
    return message

def main():
    api_key = os.getenv("DATA_GO_KR_API_KEY")
    if not api_key:
        print("[ERROR] DATA_GO_KR_API_KEY 환경변수가 설정되어 있지 않습니다.", file=sys.stderr)
        sys.exit(1)
    
    print("=== [PHASE 3] 대구 상가(상권)정보 API 수집 시작 ===")
    start_time = time.time()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    
    num_of_rows = 1000
    div_id = "ctprvnCd"
    key = "27"  # 대구광역시 시도코드
    
    # 1. 초기 1페이지 요청 및 totalCount 확인
    print("[1/3] 메타데이터 및 전체 건수 조회 중...")
    init_params = {
        "serviceKey": api_key,
        "pageNo": "1",
        "numOfRows": str(num_of_rows),
        "divId": div_id,
        "key": key,
        "type": "json"
    }
    
    try:
        resp = requests.get(API_URL, params=init_params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as e:
        print(f"[ERROR] 초기 API 요청 실패: {safe_request_error(e, api_key)}", file=sys.stderr)
        sys.exit(1)
        
    header = data.get("header", {})
    body = data.get("body", {})
    result_code = header.get("resultCode")
    
    if result_code != "00":
        print(f"[ERROR] API 응답 코드 비정상: {result_code} - {header.get('resultMsg')}", file=sys.stderr)
        sys.exit(1)
        
    total_count = int(body.get("totalCount", 0))
    total_pages = math.ceil(total_count / num_of_rows)
    print(f"  - 대구광역시 전체 상가 수 (totalCount): {total_count:,}개")
    print(f"  - 1회 요청 단위 (numOfRows): {num_of_rows}개")
    print(f"  - 총 수집 대상 페이지 수: {total_pages}페이지")
    
    # 2. 전체 페이지 순회 수집
    print(f"\n[2/3] 전체 {total_pages}페이지 순회 수집 진행 중...")
    all_items = []
    failed_pages = []
    
    # 1페이지 데이터 추가
    first_page_items = body.get("items", [])
    all_items.extend(first_page_items)
    print(f"  - [Page 1/{total_pages}] {len(first_page_items)}건 수집 완료 (누적: {len(all_items):,}건)")
    
    for page_no in range(2, total_pages + 1):
        params = {
            "serviceKey": api_key,
            "pageNo": str(page_no),
            "numOfRows": str(num_of_rows),
            "divId": div_id,
            "key": key,
            "type": "json"
        }
        
        success = False
        for attempt in range(1, 4):
            try:
                r = requests.get(API_URL, params=params, timeout=25)
                if r.status_code == 200:
                    page_data = r.json()
                    page_items = page_data.get("body", {}).get("items", [])
                    all_items.extend(page_items)
                    success = True
                    break
                else:
                    time.sleep(0.5 * attempt)
            except Exception as req_err:
                time.sleep(0.5 * attempt)
                
        if not success:
            failed_pages.append(page_no)
            print(f"  ⚠️ [Page {page_no}/{total_pages}] 3회 재시도 실패!", file=sys.stderr)
        elif page_no % 10 == 0 or page_no == total_pages:
            print(f"  - [Page {page_no}/{total_pages}] 누적 수집: {len(all_items):,}건 / {total_count:,}건 ({len(all_items)/total_count*100:.1f}%)")
            
        time.sleep(0.05)  # API rate limit 보호
        
    elapsed = time.time() - start_time
    print(f"\n수집 완료! 소요 시간: {elapsed:.1f}초")
    print(f"  - 최종 수집 건수: {len(all_items):,}건")
    if failed_pages:
        print(f"  - 실패 페이지 ({len(failed_pages)}개): {failed_pages}")
        print("[ERROR] 불완전한 데이터를 산출물로 저장하지 않습니다.", file=sys.stderr)
        sys.exit(1)
    else:
        print("  - 누락된 페이지 없이 100% 정상 수집 완료")
        
    # 3. CSV 및 메타데이터 저장
    print("\n[3/3] 원본 데이터 및 메타데이터 저장 중...")
    df = pd.DataFrame(all_items)
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    file_size = os.path.getsize(OUTPUT_FILE)
    print(f"  - CSV 저장 경로: {OUTPUT_FILE}")
    print(f"  - 파일 크기: {file_size:,} bytes ({file_size / (1024*1024):.2f} MB)")
    print(f"  - 데이터 형태: {df.shape[0]:,}행 × {df.shape[1]}열")
    
    metadata = {
        "dataset_name": "소상공인시장진흥공단_상가(상권)정보",
        "api_endpoint": API_URL,
        "region_filter": "ctprvnCd=27 (대구광역시)",
        "collection_timestamp": datetime.now().isoformat(),
        "total_count_reported": total_count,
        "total_items_collected": len(all_items),
        "total_pages": total_pages,
        "failed_pages": failed_pages,
        "output_file": str(OUTPUT_FILE),
        "file_size_bytes": file_size,
        "columns_count": df.shape[1],
        "columns_list": df.columns.tolist(),
        "elapsed_seconds": round(elapsed, 2)
    }
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    print(f"  - 메타데이터 저장 경로: {METADATA_FILE}")
    print("=== 수집 프로세스 정상 종료 ===")

if __name__ == "__main__":
    main()
