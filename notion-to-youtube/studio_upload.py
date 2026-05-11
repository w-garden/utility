"""
Windows Chrome을 원격 디버깅 모드로 실행한 뒤 Playwright로 연결해
YouTube Studio에서 재생목록 썸네일을 자동 업로드한다.
"""

import asyncio
import re
import subprocess
import time
from pathlib import Path

import requests as _requests

CDP_PORT    = 9222
EDIT_URL    = "https://studio.youtube.com/playlist/{}/edit"
# WSL2에서 Windows 실행파일 직접 호출 (PowerShell 우회)
CHROME_WSL_EXE  = "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"
CHROME_WIN_PROFILE = "C:\\temp\\yt_studio_profile"  # Chrome이 받을 Windows 경로


def _chrome_running() -> bool:
    """포트 9222에 Chrome이 응답하는지 확인"""
    try:
        _requests.get(f"http://localhost:{CDP_PORT}/json/version", timeout=2)
        return True
    except Exception:
        return False


def _launch_chrome() -> bool:
    """WSL2에서 Windows Chrome을 원격 디버깅 모드로 시작"""
    try:
        subprocess.Popen([
            CHROME_WSL_EXE,
            f"--remote-debugging-port={CDP_PORT}",
            f"--user-data-dir={CHROME_WIN_PROFILE}",
            "--no-first-run",
            "--no-default-browser-check",
        ])
    except FileNotFoundError:
        print(f"  Chrome을 찾을 수 없습니다: {CHROME_WSL_EXE}")
        return False

    for _ in range(20):
        time.sleep(1)
        if _chrome_running():
            return True
    return False


async def _upload_async(playlist_id: str, image_path: Path) -> bool:
    from playwright.async_api import async_playwright  # noqa: PLC0415

    if not _chrome_running():
        print("  Windows Chrome 시작 중...")
        if not _launch_chrome():
            print("  Chrome을 찾을 수 없습니다. 수동 업로드가 필요합니다.")
            return False

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(f"http://localhost:{CDP_PORT}")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()

        try:
            # 로그인 확인
            await page.goto("https://studio.youtube.com/")
            await page.wait_for_load_state("networkidle", timeout=15000)

            # 로그인 페이지로 리디렉션되면 수동 로그인 요청
            if "accounts.google.com" in page.url or "signin" in page.url:
                print("  브라우저에서 Google 계정으로 로그인 후 Enter를 눌러주세요.")
                input()

            # 재생목록 편집 페이지로 이동
            await page.goto(EDIT_URL.format(playlist_id))
            await page.wait_for_load_state("networkidle", timeout=20000)

            # 썸네일 영역 클릭
            thumb = page.locator(
                "ytcp-thumbnail-with-preferences, ytcp-image-file-upload, [test-id='thumbnail-wrapper']"
            ).first
            if await thumb.count():
                await thumb.click()
                await page.wait_for_timeout(1000)

            # 파일 input에 이미지 설정
            # image_path가 WSL2 경로이므로 Windows 경로로 변환
            win_path = subprocess.check_output(
                ["wslpath", "-w", str(image_path)], text=True
            ).strip()

            file_input = page.locator("input[type='file']").first
            await file_input.set_input_files(win_path)
            await page.wait_for_timeout(2000)

            # 저장
            save = page.get_by_role("button", name=re.compile(r"저장|Save", re.I)).first
            if await save.count():
                await save.click()
                await page.wait_for_timeout(3000)
                print("  썸네일 자동 업로드 성공!")
            else:
                print("  저장 버튼을 못 찾았습니다. 브라우저에서 직접 저장해주세요.")
                input("  완료 후 Enter: ")

            return True

        except Exception as e:
            print(f"  자동화 실패: {e}")
            return False
        finally:
            await page.close()


def upload(playlist_id: str, image_path: Path) -> bool:
    try:
        return asyncio.run(_upload_async(playlist_id, image_path))
    except Exception as e:
        print(f"  Playwright 오류: {e}")
        return False
