from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

THUMB_W, THUMB_H = 1280, 720
BG_COLOR      = (15, 20, 40)
LINE_COLOR    = (80, 120, 220)
DATE_COLOR    = (255, 255, 255)
WORSHIP_COLOR = (160, 190, 255)

THUMBNAIL_PATH = Path(__file__).parent / "thumbnail.png"

_FONT_CANDIDATES = [
    "/mnt/c/Windows/Fonts/malgunbd.ttf",   # 맑은 고딕 Bold (WSL2)
    "/mnt/c/Windows/Fonts/malgun.ttf",
    "/mnt/c/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",  # macOS
    "/Library/Fonts/AppleGothic.ttf",
]


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in _FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size)


def generate(title: str, output: Path = THUMBNAIL_PATH) -> Path:
    """
    제목 텍스트로 YouTube 썸네일 이미지(1280×720)를 생성하고 저장한다.
    날짜 부분(숫자/공백/점/-)과 '예배 찬양' 부분을 분리해서 2줄로 그린다.
    """
    img = Image.new("RGB", (THUMB_W, THUMB_H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # 제목 분리: "2026.05.11 - 2026.05.17 예배 찬양"
    if "예배" in title:
        idx = title.rfind("예배")
        date_part = title[:idx].strip()
        worship_part = title[idx:].strip()
    else:
        date_part = title
        worship_part = ""

    font_date    = _load_font(88)
    font_worship = _load_font(60)

    def text_width(text, font):
        bb = draw.textbbox((0, 0), text, font=font)
        return bb[2] - bb[0], bb[3] - bb[1]

    dw, dh = text_width(date_part, font_date)
    ww, wh = text_width(worship_part, font_worship) if worship_part else (0, 0)

    total_h = dh + (30 + wh if worship_part else 0)
    top_y   = (THUMB_H - total_h) // 2 - 20

    # 날짜 텍스트
    draw.text(((THUMB_W - dw) // 2, top_y), date_part, font=font_date, fill=DATE_COLOR)

    # 구분선
    line_y = top_y + dh + 18
    draw.line([(120, line_y), (THUMB_W - 120, line_y)], fill=LINE_COLOR, width=3)

    # 예배 찬양 텍스트
    if worship_part:
        draw.text(((THUMB_W - ww) // 2, line_y + 18), worship_part, font=font_worship, fill=WORSHIP_COLOR)

    img.save(output, "PNG")
    return output


def upload(service, playlist_id: str, image_path: Path) -> bool:
    """재생목록 썸네일 업로드 시도. 성공 여부 반환."""
    from googleapiclient.http import MediaFileUpload  # noqa: PLC0415
    try:
        media = MediaFileUpload(str(image_path), mimetype="image/png", resumable=False)
        # YouTube API 공식 미지원이지만 playlistId 파라미터로 시도
        req = service.thumbnails().set(videoId=playlist_id, media_body=media)
        req.uri = req.uri.replace("videoId=", "playlistId=")
        req.execute()
        return True
    except Exception as e:
        print(f"  썸네일 자동 업로드 실패: {e}")
        return False
