import os
import platform
import subprocess
from datetime import date

from notion_client import Client

DATABASE_ID = "189c89f9-799c-83ee-a2ae-871edbea4dec"

_client: Client | None = None


def get_notion_token() -> str:
    token = os.environ.get("NOTION_TOKEN")
    if token:
        return token

    # WSL2 → Windows Credential Manager
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command",
             "(Get-StoredCredential -Target mcp-notion).GetNetworkCredential().Password"],
            capture_output=True, text=True, timeout=5,
        )
        token = result.stdout.strip().rstrip("\r\n")
        if token:
            return token
    except Exception:
        pass

    # macOS Keychain
    if platform.system() == "Darwin":
        try:
            result = subprocess.run(
                ["security", "find-generic-password", "-s", "mcp-notion",
                 "-a", os.environ.get("USER", ""), "-w"],
                capture_output=True, text=True, check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            pass

    raise RuntimeError(
        "Notion 토큰을 찾을 수 없습니다.\n"
        "환경변수 NOTION_TOKEN을 설정하거나 Keychain에 'mcp-notion'으로 저장하세요.\n"
        "  WSL2: export NOTION_TOKEN=secret_..."
    )


def _get_client() -> Client:
    global _client
    if _client is None:
        _client = Client(auth=get_notion_token())
    return _client


def _get_block_children(block_id: str) -> list:
    client = _get_client()
    blocks = []
    cursor = None
    while True:
        resp = client.blocks.children.list(block_id=block_id, start_cursor=cursor)
        blocks.extend(resp["results"])
        if not resp.get("has_more"):
            break
        cursor = resp["next_cursor"]
    return blocks


_TEXT_BLOCK_TYPES = {
    "paragraph", "numbered_list_item", "bulleted_list_item",
    "to_do", "toggle", "quote", "callout",
}


def _extract_youtube_urls(blocks: list) -> list[str]:
    urls = []
    for block in blocks:
        btype = block.get("type", "")

        if btype == "video":
            video = block.get("video", {})
            url = (video.get("external") or {}).get("url", "")
            if not url:
                url = (video.get("file") or {}).get("url", "")
            if "youtu" in url:
                urls.append(url)

        elif btype in _TEXT_BLOCK_TYPES:
            rich_texts = (block.get(btype) or {}).get("rich_text", [])
            for rt in rich_texts:
                # href 링크
                href = (rt.get("href") or "")
                if "youtu" in href:
                    urls.append(href)
                    continue
                # 평문 텍스트에 URL이 직접 적힌 경우
                text = (rt.get("plain_text") or "").strip()
                if "youtu" in text and text.startswith("http"):
                    urls.append(text)

        if block.get("has_children"):
            urls.extend(_extract_youtube_urls(_get_block_children(block["id"])))
    return urls


def get_pages_in_range(start: date, end: date) -> list[dict]:
    client = _get_client()
    pages = []
    cursor = None
    while True:
        kwargs: dict = dict(
            filter={
                "and": [
                    {"property": "날짜", "date": {"on_or_after": start.isoformat()}},
                    {"property": "날짜", "date": {"on_or_before": end.isoformat()}},
                ]
            },
            sorts=[{"property": "날짜", "direction": "ascending"}],
        )
        if cursor:
            kwargs["start_cursor"] = cursor
        resp = client.data_sources.query(DATABASE_ID, **kwargs)
        pages.extend(resp["results"])
        if not resp.get("has_more"):
            break
        cursor = resp["next_cursor"]
    return pages


def get_youtube_urls_for_week(start: date, end: date) -> list[tuple[str, str, list[str]]]:
    """
    주어진 날짜 범위에서 YouTube URL 목록 반환.
    Returns: [(page_title, date_str, [url, ...]), ...]
    """
    pages = get_pages_in_range(start, end)
    result = []
    for page in pages:
        title_parts = page["properties"]["제목"]["title"]
        title = title_parts[0]["plain_text"] if title_parts else "제목 없음"
        date_prop = page["properties"]["날짜"]["date"]
        date_str = date_prop["start"] if date_prop else ""
        blocks = _get_block_children(page["id"])
        urls = _extract_youtube_urls(blocks)
        if urls:
            result.append((title, date_str, urls))
    return result
