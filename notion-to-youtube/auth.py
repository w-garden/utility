"""
GitHub Gist에서 OAuth 자격증명을 읽어 YouTube API 서비스를 반환한다.
디스크에 평문 자격증명을 쓰지 않고 메모리에서만 사용한다.
"""

import json
import os
import platform
import subprocess

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube"]
_GIST_API = "https://api.github.com/gists/{gist_id}"


def get_github_pat() -> str:
    # 1순위: 환경변수 (WSL2, CI 등)
    pat = os.environ.get("GITHUB_PAT")
    if pat:
        return pat

    username = os.environ.get("USER") or os.environ.get("USERNAME", "")

    # 2순위: keyring (macOS Keychain / Windows Credential Manager)
    try:
        import keyring  # noqa: PLC0415
        pat = keyring.get_password("github-pat-gist", username)
        if pat:
            return pat
    except Exception:
        pass

    # 3순위: WSL2 → Windows Credential Manager (cmdkey via powershell.exe)
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command",
             f"(Get-StoredCredential -Target github-pat-gist).GetNetworkCredential().Password"],
            capture_output=True, text=True, timeout=5,
        )
        pat = result.stdout.strip().rstrip("\r\n")
        if pat:
            return pat
    except Exception:
        pass

    # 5순위: macOS security 명령어 직접 호출
    if platform.system() == "Darwin":
        try:
            result = subprocess.run(
                ["security", "find-generic-password", "-s", "github-pat-gist", "-a", username, "-w"],
                capture_output=True, text=True, check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            pass

    raise RuntimeError(
        "GitHub PAT을 찾을 수 없습니다.\n"
        "다음 중 하나로 저장하세요:\n"
        "  macOS:   security add-generic-password -U -s github-pat-gist -a $USER -w <PAT>\n"
        "  Windows: cmdkey /generic:github-pat-gist /user:%USERNAME% /pass:<PAT>\n"
        "  WSL2:    export GITHUB_PAT=<PAT>"
    )


def _gist_get(gist_id: str, pat: str) -> dict:
    headers = {"Authorization": f"token {pat}", "Accept": "application/vnd.github+json"}
    resp = requests.get(_GIST_API.format(gist_id=gist_id), headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _gist_patch(gist_id: str, pat: str, files: dict) -> None:
    headers = {"Authorization": f"token {pat}", "Accept": "application/vnd.github+json"}
    resp = requests.patch(
        _GIST_API.format(gist_id=gist_id),
        headers=headers,
        json={"files": files},
        timeout=10,
    )
    resp.raise_for_status()


def _get_gist_file(gist_id: str, pat: str, filename: str) -> str | None:
    data = _gist_get(gist_id, pat)
    file_entry = data["files"].get(filename)
    if not file_entry:
        return None
    # 내용이 truncated일 때 raw_url에서 전체 가져오기
    if file_entry.get("truncated"):
        resp = requests.get(file_entry["raw_url"], timeout=10)
        resp.raise_for_status()
        return resp.text
    return file_entry["content"]


def get_youtube_service(gist_id: str):
    """인증된 YouTube Data API v3 서비스 객체 반환."""
    from googleapiclient.discovery import build  # noqa: PLC0415

    pat = get_github_pat()

    # OAuth client config
    client_json = _get_gist_file(gist_id, pat, "youtube_oauth.json")
    if not client_json:
        raise RuntimeError("Gist에 youtube_oauth.json 파일이 없습니다. SETUP.md Step 2를 확인하세요.")
    client_config = json.loads(client_json)

    client_id = client_config["installed"]["client_id"]
    client_secret = client_config["installed"]["client_secret"]
    token_uri = client_config["installed"]["token_uri"]

    # 저장된 refresh token 시도
    refresh_json = _get_gist_file(gist_id, pat, "youtube_refresh_token.json")
    if refresh_json:
        token_data = json.loads(refresh_json)
        creds = Credentials(
            token=None,
            refresh_token=token_data["refresh_token"],
            token_uri=token_uri,
            client_id=client_id,
            client_secret=client_secret,
            scopes=SCOPES,
        )
        creds.refresh(Request())
    else:
        # 첫 실행: 브라우저 OAuth flow
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
        creds = flow.run_local_server(port=0)
        # refresh token을 Gist에 저장
        _gist_patch(gist_id, pat, {
            "youtube_refresh_token.json": {
                "content": json.dumps({"refresh_token": creds.refresh_token})
            }
        })
        print("refresh token을 Gist에 저장했습니다.")

    return build("youtube", "v3", credentials=creds)
