"""
생명의 삶 (두란노) 오늘의 QT 성경 본문 스크래퍼
사용법:
  python scrape_qt.py                    # 오늘 날짜, 우리말성경
  python scrape_qt.py 2026-04-23         # 특정 날짜, 우리말성경
  python scrape_qt.py 2026-04-23 k       # 특정 날짜, 개역개정 (k=개역개정, w=우리말성경)
"""

import sys
import urllib.request
from lxml import html as lxml_html
from datetime import date


def scrape_qt(qt_date: str = None, translation: str = "w") -> dict:
    if qt_date is None:
        qt_date = date.today().isoformat()

    url = f"https://www.duranno.com/qt/view/bible.asp?qtDate={qt_date}&d={translation}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

    with urllib.request.urlopen(req) as r:
        raw = r.read()

    tree = lxml_html.fromstring(raw.decode("euc-kr", errors="replace"))

    # 성경 범위 + 메인 제목
    h1 = tree.cssselect("h1")
    bible_ref = ""
    main_title = ""
    for tag in h1:
        span = tag.cssselect("span")
        em = tag.cssselect("em")
        if span and em:
            bible_ref = span[0].text_content().replace("\xa0", " ").strip()
            main_title = em[0].text_content().replace("\xa0", " ").strip()
            break

    # 번역 이름
    translation_name = "우리말성경" if translation == "w" else "개역개정"

    # 본문: div.bible 안의 소제목 + 절
    bible_div = tree.cssselect("div.bible")
    sections = []
    if bible_div:
        current_subtitle = None
        current_verses = []
        for child in bible_div[0]:
            tag_name = child.tag.lower()
            cls = child.get("class", "")

            if tag_name == "p" and "title" in cls:
                if current_subtitle is not None or current_verses:
                    sections.append({"subtitle": current_subtitle, "verses": current_verses})
                current_subtitle = child.text_content().strip()
                current_verses = []

            elif tag_name == "table":
                th = child.cssselect("th")
                td = child.cssselect("td")
                if th and td:
                    verse_num = th[0].text_content().strip()
                    verse_text = td[0].text_content().strip()
                    current_verses.append((verse_num, verse_text))

        if current_subtitle is not None or current_verses:
            sections.append({"subtitle": current_subtitle, "verses": current_verses})

    return {
        "date": qt_date,
        "translation": translation_name,
        "bible_ref": bible_ref,
        "main_title": main_title,
        "sections": sections,
    }


def format_output(data: dict) -> str:
    lines = []
    lines.append(f"[{data['date']}] {data['translation']}")
    lines.append("")
    lines.append(data["bible_ref"])
    lines.append(data["main_title"])
    lines.append("")

    for section in data["sections"]:
        if section["subtitle"]:
            lines.append(section["subtitle"])
            lines.append("")
        for num, text in section["verses"]:
            lines.append(f"{num}\t{text}")
        lines.append("")

    return "\n".join(lines).strip()


if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    qt_date = sys.argv[1] if len(sys.argv) > 1 else None
    translation = sys.argv[2] if len(sys.argv) > 2 else "w"

    data = scrape_qt(qt_date, translation)
    print(format_output(data))
