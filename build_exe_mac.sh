#!/bin/bash
cd "$(dirname "$0")"

if ! command -v python3 &>/dev/null; then
    echo "[오류] Python3가 설치되어 있지 않습니다. brew install python3"
    exit 1
fi

python3 -m pip install python-pptx pyinstaller --quiet
pyinstaller --onefile --windowed --name update_pptx update_pptx.py

echo "완료: dist/update_pptx"
