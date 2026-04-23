"""
생명의 삶 QT 성경 본문 → Notion 자동 저장

사용법:
  set NOTION_TOKEN=secret_xxxxx   (한 번만 설정)
  python qt_to_notion.py                   # 오늘 날짜, 우리말성경
  python qt_to_notion.py 2026-04-24        # 특정 날짜
  python qt_to_notion.py 2026-04-24 k      # 특정 날짜, 개역개정

Notion 토큰 발급:
  1. https://www.notion.so/my-integrations 에서 통합(integration) 생성
  2. 'secret_'으로 시작하는 토큰 복사
  3. Notion에서 QT 데이터베이스 페이지 열고 우측 상단 '...' → '연결(Connections)' → 생성한 통합 추가
"""

import sys
import os
import re
from datetime import date
from pathlib import Path
import requests
from dotenv import load_dotenv
from scrape_qt import scrape_qt

# 스크립트와 같은 폴더의 .env 파일 로드
load_dotenv(Path(__file__).parent / ".env")

# ── 설정 ────────────────────────────────────────────────────────────────────
NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
DATABASE_ID  = "c0cc89f9799c824e997d81395581c03a"   # QT > 일기 DB
# ────────────────────────────────────────────────────────────────────────────

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}


def check_existing(qt_date: str) -> bool:
    """해당 날짜 항목이 이미 있는지 확인"""
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    r = requests.post(url, headers=HEADERS, json={
        "filter": {"property": "날짜", "date": {"equals": qt_date}}
    })
    r.raise_for_status()
    return len(r.json().get("results", [])) > 0


def _text(content: str, bold: bool = False) -> dict:
    block = {"type": "text", "text": {"content": content}}
    if bold:
        block["annotations"] = {"bold": True}
    return block


def build_blocks(data: dict) -> list:
    """스크랩 데이터를 Notion 블록 리스트로 변환"""
    # 성경 범위 정리 (공백 정규화)
    bible_ref = re.sub(r"\s+", " ", data["bible_ref"]).strip()

    blocks = []

    # 1. 본문
    blocks += [
        {"object": "block", "type": "paragraph", "paragraph": {
            "rich_text": [_text(f"1. 본문 : {bible_ref}", bold=True)],
            "color": "gray_background"
        }},
        {"object": "block", "type": "paragraph", "paragraph": {"rich_text": []}},
    ]

    # 성경 본문 (소제목 + 절) — 1. 본문 바로 아래
    for section in data["sections"]:
        if section["subtitle"]:
            blocks.append({"object": "block", "type": "heading_3", "heading_3": {
                "rich_text": [_text(section["subtitle"])]
            }})
        for num, text in section["verses"]:
            blocks.append({"object": "block", "type": "paragraph", "paragraph": {
                "rich_text": [_text(f"{num}  ", bold=True), _text(text)]
            }})
        blocks.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": []}})

    # 2. 제목
    blocks += [
        {"object": "block", "type": "paragraph", "paragraph": {
            "rich_text": [_text(f"2. 제목 : {data['main_title']}", bold=True)],
            "color": "gray_background"
        }},
        {"object": "block", "type": "paragraph", "paragraph": {"rich_text": []}},
    ]

    # 묵상 섹션 (빈 칸)
    for label in [
        "3. 묵상내용 :",
        "4. 기도 :",
        "5. 적용 : 내가 다음에 할 행동은 무엇인가요?",
    ]:
        blocks += [
            {"object": "block", "type": "paragraph", "paragraph": {
                "rich_text": [_text(label, bold=True)],
                "color": "gray_background"
            }},
            {"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {
                "rich_text": [_text("")]
            }},
        ]

    return blocks


def create_notion_page(data: dict) -> str:
    r = requests.post(
        "https://api.notion.com/v1/pages",
        headers=HEADERS,
        json={
            "parent": {"database_id": DATABASE_ID},
            "icon": {"type": "emoji", "emoji": "➖"},
            "properties": {
                "제목": {"title": [{"text": {"content": data["main_title"]}}]},
                "날짜": {"date": {"start": data["date"]}},
                "본문": {"rich_text": [{"text": {"content": re.sub(r"\s+", " ", data["bible_ref"]).strip()}}]},
            },
            "children": build_blocks(data),
        },
    )
    r.raise_for_status()
    return r.json().get("url", "")


def main():
    if not NOTION_TOKEN:
        print("오류: NOTION_TOKEN 환경변수를 먼저 설정해주세요.")
        print("  Windows: set NOTION_TOKEN=secret_xxxxx")
        sys.exit(1)

    qt_date = date.today().isoformat()

    # 로컬 실행 시 대화형 입력, GitHub Actions 등 비대화형 환경에서는 환경변수 사용
    if sys.stdin.isatty():
        trans_input = input("역본 선택 (w=우리말성경, k=개역개정, 기본값 w): ").strip().lower()
        translation = trans_input if trans_input in ("w", "k") else "w"
    else:
        translation = os.environ.get("QT_TRANSLATION", "w")

    print(f"[{qt_date}] 기존 항목 확인 중...")
    if check_existing(qt_date):
        print(f"  → 이미 존재합니다. 건너뜁니다.")
        return

    print("  → 없음. QT 본문 스크랩 중...")
    data = scrape_qt(qt_date, translation)

    if not data["main_title"]:
        print(f"  → {qt_date} QT 내용이 아직 사이트에 없습니다. 건너뜁니다.")
        return

    print(f"  → {data['bible_ref'].strip()}  {data['main_title']}")

    print("  → Notion 페이지 생성 중...")
    page_url = create_notion_page(data)
    print(f"완료! {page_url}")


if __name__ == "__main__":
    main()


