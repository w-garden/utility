import io
import json
import os
import uuid
from datetime import date, datetime, timedelta, timezone

import boto3

BUCKET = os.environ["BUCKET_NAME"]
APP_PASSWORD = os.environ.get("APP_PASSWORD", "")
LOG_TABLE = os.environ.get("LOG_TABLE", "")
s3 = boto3.client("s3", region_name="ap-northeast-2",
                  endpoint_url="https://s3.ap-northeast-2.amazonaws.com")
dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-2")


def _log(event: dict, action: str, extra: dict = None):
    if not LOG_TABLE:
        return
    try:
        now = datetime.now(timezone.utc)
        ip = (event.get("requestContext", {})
                   .get("identity", {})
                   .get("sourceIp", "unknown"))
        item = {
            "id": str(uuid.uuid4()),
            "timestamp": now.isoformat(),
            "action": action,
            "ip": ip,
        }
        if extra:
            item.update(extra)
        dynamodb.Table(LOG_TABLE).put_item(Item=item)
    except Exception:
        pass


def _html(body: str, status: int = 200) -> dict:
    return {"statusCode": status, "headers": {"Content-Type": "text/html; charset=utf-8"}, "body": body}


def _json(data: dict, status: int = 200) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps(data, ensure_ascii=False),
    }


def _check_password(body: dict) -> bool:
    if not APP_PASSWORD:
        return True
    return body.get("password") == APP_PASSWORD


def _next_wednesday() -> str:
    today = date.today()
    days = (2 - today.weekday()) % 7
    return (today + timedelta(days=days)).strftime("%Y%m%d")


def handle_upload_url(body: dict) -> dict:
    if not _check_password(body):
        return _json({"error": "비밀번호가 틀렸습니다."}, 401)

    filenames = body.get("filenames", [])
    if not filenames:
        return _json({"error": "filenames가 비어있습니다."}, 400)

    session_id = str(uuid.uuid4())[:8]
    urls = []
    for i, name in enumerate(filenames):
        ext = name.rsplit(".", 1)[-1] if "." in name else "jpg"
        key = f"uploads/{session_id}/{i+1}.{ext}"
        url = s3.generate_presigned_url(
            "put_object",
            Params={"Bucket": BUCKET, "Key": key},
            ExpiresIn=300,
        )
        urls.append({"filename": name, "key": key, "url": url})

    return _json({"session_id": session_id, "uploads": urls})


def handle_generate(body: dict) -> dict:
    if not _check_password(body):
        return _json({"error": "비밀번호가 틀렸습니다."}, 401)

    session_id = body.get("session_id")
    keys = body.get("keys", [])
    title = body.get("title", f"{_next_wednesday()} 수요성령집회 콘티")
    split = int(body.get("split", 1))

    if not keys:
        return _json({"error": "keys가 비어있습니다."}, 400)

    from pptx import Presentation  # noqa: PLC0415
    from pptx.util import Emu, Pt  # noqa: PLC0415
    from pptx.enum.text import PP_ALIGN, MSO_AUTO_SIZE  # noqa: PLC0415

    prs = Presentation()
    blank = prs.slide_layouts[6]
    slide_w = prs.slide_width
    slide_h = prs.slide_height

    split = max(1, min(split, len(keys) - 1)) if len(keys) > 1 else len(keys)
    groups = [keys[:split], keys[split:]] if len(keys) > 1 else [keys, []]

    for slide_idx, group in enumerate(groups):
        if not group:
            continue
        slide = prs.slides.add_slide(blank)

        top_offset = Emu(0)
        if slide_idx == 0:
            tb_h = Pt(32)
            txBox = slide.shapes.add_textbox(Emu(0), Emu(0), slide_w, tb_h)
            tf = txBox.text_frame
            tf.auto_size = MSO_AUTO_SIZE.SHAPE_TO_FIT_TEXT
            tf.margin_top = Emu(0)
            tf.margin_bottom = Emu(0)
            tf.margin_left = Emu(0)
            tf.margin_right = Emu(0)
            run = tf.paragraphs[0].add_run()
            tf.paragraphs[0].alignment = PP_ALIGN.LEFT
            run.text = title
            run.font.size = Pt(22)
            run.font.bold = False
            run.font.name = '맑은 고딕'
            top_offset = tb_h + Pt(2)

        n = len(group)
        img_w = slide_w // n
        img_h = slide_h - top_offset

        for i, key in enumerate(group):
            obj = s3.get_object(Bucket=BUCKET, Key=key)
            img_data = io.BytesIO(obj["Body"].read())
            slide.shapes.add_picture(img_data, img_w * i, top_offset, img_w, img_h)

    out = io.BytesIO()
    prs.save(out)
    out.seek(0)

    out_key = f"outputs/{session_id}/{title}.pptx"
    s3.put_object(Bucket=BUCKET, Key=out_key, Body=out.read(), ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation")

    download_url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET, "Key": out_key},
        ExpiresIn=3600,
    )

    return _json({"message": "완료!", "download_url": download_url, "title": title})


def lambda_handler(event, context):
    from pathlib import Path  # noqa: PLC0415
    method = event.get("httpMethod", "GET")
    path = event.get("path", "/")

    if method == "GET" and path == "/":
        _log(event, "page_view")
        html = (Path(__file__).parent / "templates" / "index.html").read_text()
        return _html(html)

    if method == "POST":
        body = json.loads(event.get("body") or "{}")
        if path == "/upload-url":
            return handle_upload_url(body)
        if path == "/generate":
            result = handle_generate(body)
            if result["statusCode"] == 200:
                _log(event, "generate", {
                    "title": body.get("title", ""),
                    "image_count": len(body.get("keys", [])),
                })
            return result

    return _json({"error": "Not found"}, 404)
