"""
notion-to-youtube: Notion 스케쥴 DB의 YouTube URL을 주별 재생목록으로 생성하는 CLI
"""

import argparse
import configparser
from datetime import date, timedelta
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config.ini"


def load_config() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"config.ini가 없습니다: {CONFIG_PATH}")
    cfg.read(CONFIG_PATH)
    return cfg


def week_range(ref: date) -> tuple[date, date]:
    """ref 날짜가 속한 주의 월요일~일요일 반환"""
    monday = ref - timedelta(days=ref.weekday())
    return monday, monday + timedelta(days=6)


def cmd_auth(args) -> None:
    cfg = load_config()
    gist_id = cfg["github"]["gist_id"]
    if gist_id == "YOUR_GIST_ID_HERE":
        raise ValueError("config.ini의 gist_id를 실제 값으로 바꿔주세요.")

    from auth import get_youtube_service  # noqa: PLC0415
    print("YouTube API 인증 중...")
    service = get_youtube_service(gist_id)
    result = service.channels().list(part="snippet", mine=True).execute()
    channel = result["items"][0]["snippet"]["title"]
    print(f"인증 성공! 채널: {channel}")


def cmd_sync(args) -> None:
    cfg = load_config()
    gist_id = cfg["github"]["gist_id"]
    playlist_id = cfg.get("youtube", "playlist_id", fallback="").strip() or None

    # 날짜 범위 결정 (월~일)
    if args.date:
        ref = date.fromisoformat(args.date)
    elif args.last_week:
        ref = date.today() - timedelta(weeks=1)
    else:
        ref = date.today()

    start, end = week_range(ref)
    print(f"날짜 범위: {start} ~ {end}")

    from schedule import get_youtube_urls_for_week  # noqa: PLC0415
    from youtube_client import sync_playlist        # noqa: PLC0415

    entries = get_youtube_urls_for_week(start, end)
    if not entries:
        print("해당 기간에 YouTube URL이 있는 페이지가 없습니다.")
        return

    all_urls: list[str] = []
    for title, date_str, urls in entries:
        print(f"\n  [{date_str}] {title}")
        for url in urls:
            print(f"    {url}")
            all_urls.append(url)

    playlist_title = args.title or f"{start.strftime('%Y.%m.%d')} - {end.strftime('%Y.%m.%d')} 예배 찬양"
    print(f"\n재생목록 동기화 중: '{playlist_title}' ({len(all_urls)}곡)")
    new_id = sync_playlist(gist_id, playlist_id, playlist_title, all_urls)

    # 신규 생성된 경우 config.ini에 playlist_id 저장
    if new_id != playlist_id:
        if not cfg.has_section("youtube"):
            cfg.add_section("youtube")
        cfg.set("youtube", "playlist_id", new_id)
        with open(CONFIG_PATH, "w") as f:
            cfg.write(f)
        print("playlist_id를 config.ini에 저장했습니다.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Notion 스케쥴 DB → YouTube 주별 재생목록 자동 생성"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    auth_parser = subparsers.add_parser("auth", help="YouTube API 인증 테스트")
    auth_parser.set_defaults(func=cmd_auth)

    sync_parser = subparsers.add_parser("sync", help="주별 재생목록 동기화")
    sync_parser.add_argument("--date", "-d", help="기준 날짜 (YYYY-MM-DD), 기본값: 오늘")
    sync_parser.add_argument("--last-week", "-l", action="store_true", help="지난 주 기준")
    sync_parser.add_argument("--title", "-t", help="재생목록 제목 (기본값: 날짜 자동 생성)")
    sync_parser.set_defaults(func=cmd_sync)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
