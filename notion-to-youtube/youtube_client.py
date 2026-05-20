import re

from auth import get_youtube_service


def _extract_video_id(url: str) -> str | None:
    for pattern in [
        r"youtu\.be/([a-zA-Z0-9_-]{11})",
        r"youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})",
        r"youtube\.com/embed/([a-zA-Z0-9_-]{11})",
    ]:
        m = re.search(pattern, url)
        if m:
            return m.group(1)
    return None


def _clear_playlist(service, playlist_id: str) -> None:
    """재생목록의 모든 항목 삭제"""
    cursor = None
    while True:
        kwargs = {"part": "id", "playlistId": playlist_id, "maxResults": 50}
        if cursor:
            kwargs["pageToken"] = cursor
        resp = service.playlistItems().list(**kwargs).execute()
        for item in resp.get("items", []):
            service.playlistItems().delete(id=item["id"]).execute()
        cursor = resp.get("nextPageToken")
        if not cursor:
            break


def sync_playlist(gist_id: str, playlist_id: str | None, title: str, urls: list[str]) -> str:
    """
    재생목록을 동기화한다.
    - playlist_id가 있으면 내용을 비우고 제목 갱신 후 재추가
    - 없으면 새로 생성
    playlist_id를 반환한다.
    """
    service = get_youtube_service(gist_id)

    if playlist_id:
        print(f"기존 재생목록 초기화 중...")
        _clear_playlist(service, playlist_id)
        service.playlists().update(
            part="snippet",
            body={
                "id": playlist_id,
                "snippet": {"title": title},
            },
        ).execute()
    else:
        print("재생목록 신규 생성 중...")
        resp = service.playlists().insert(
            part="snippet,status",
            body={
                "snippet": {"title": title},
                "status": {"privacyStatus": "private"},
            },
        ).execute()
        playlist_id = resp["id"]

    added = 0
    for url in urls:
        video_id = _extract_video_id(url)
        if not video_id:
            print(f"  건너뜀 (ID 파싱 불가): {url}")
            continue
        try:
            service.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": playlist_id,
                        "resourceId": {"kind": "youtube#video", "videoId": video_id},
                    }
                },
            ).execute()
            added += 1
        except Exception as e:
            err = str(e)
            if "quotaExceeded" in err:
                print(f"  YouTube API 일일 할당량 초과 — 내일 다시 실행해주세요.")
                break
            print(f"  추가 실패 ({video_id}): {e}")

    print(f"동기화 완료: '{title}' — {added}/{len(urls)}곡")
    print(f"  https://www.youtube.com/playlist?list={playlist_id}")


    return playlist_id
