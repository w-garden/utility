"""
AWS Lambda 핸들러.
GET /       → index.html 반환
POST /sync  → Notion → YouTube 재생목록 동기화
"""

import json
import os
from datetime import date, timedelta
from pathlib import Path


def _week_range(ref: date) -> tuple[date, date]:
    monday = ref - timedelta(days=ref.weekday())
    return monday, monday + timedelta(days=6)


def _html_response(body: str, status: int = 200) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "text/html; charset=utf-8"},
        "body": body,
    }


def _json_response(data: dict, status: int = 200) -> dict:
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(data, ensure_ascii=False),
    }


def _check_password(body: dict) -> bool:
    app_password = os.environ.get("APP_PASSWORD", "")
    if not app_password:
        return True  # 환경변수 미설정 시 인증 생략
    return body.get("password") == app_password


def handle_sync(body: dict) -> dict:
    if not _check_password(body):
        return _json_response({"error": "비밀번호가 틀렸습니다."}, 401)

    try:
        ref_str = body.get("date", date.today().isoformat())
        ref = date.fromisoformat(ref_str)
        start, end = _week_range(ref)

        from schedule import get_youtube_urls_for_week  # noqa: PLC0415
        from youtube_client import sync_playlist         # noqa: PLC0415

        gist_id    = os.environ["GIST_ID"]
        playlist_id = os.environ.get("PLAYLIST_ID", "").strip() or None

        entries = get_youtube_urls_for_week(start, end)
        if not entries:
            return _json_response({
                "message": "해당 기간에 YouTube URL이 없습니다.",
                "start": start.isoformat(),
                "end": end.isoformat(),
            })

        all_urls: list[str] = []
        pages = []
        for title, date_str, urls in entries:
            all_urls.extend(urls)
            pages.append({"title": title, "date": date_str, "count": len(urls)})

        playlist_title = f"{start.strftime('%Y.%m.%d')} - {end.strftime('%Y.%m.%d')} 예배 찬양"
        new_id = sync_playlist(gist_id, playlist_id, playlist_title, all_urls)

        return _json_response({
            "message": "동기화 완료!",
            "playlist_url": f"https://www.youtube.com/playlist?list={new_id}",
            "title": playlist_title,
            "pages": pages,
            "total": len(all_urls),
        })

    except Exception as e:
        return _json_response({"error": str(e)}, 500)


def lambda_handler(event, context):
    method = event.get("httpMethod", "GET")
    path   = event.get("path", "/")

    if method == "GET" and path == "/":
        html = (Path(__file__).parent / "templates" / "index.html").read_text()
        return _html_response(html)

    if method == "POST" and path == "/sync":
        body = json.loads(event.get("body") or "{}")
        return handle_sync(body)

    return _json_response({"error": "Not found"}, 404)
