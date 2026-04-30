#!/bin/bash
echo "============================================="
echo "  update_pptx 실행파일 빌드 스크립트 (Mac)"
echo "============================================="
echo

# Python3 설치 확인
if ! command -v python3 &>/dev/null; then
    echo "[오류] Python3가 설치되어 있지 않습니다."
    echo "터미널에서 'brew install python3' 로 설치 후 다시 실행하세요."
    exit 1
fi

echo "[1/3] 필요 패키지 설치 중..."
python3 -m pip install python-pptx pyinstaller --quiet

echo "[2/3] 실행파일 빌드 중..."
pyinstaller --onefile --console --name update_pptx update_pptx.py

echo "[3/3] 배포 폴더 구성 중..."
mkdir -p 배포
cp dist/update_pptx 배포/update_pptx
cp config.ini 배포/config.ini
chmod +x 배포/update_pptx

echo
echo "============================================="
echo "  완료! '배포' 폴더 안의 두 파일을 전달하세요:"
echo "    - update_pptx"
echo "    - config.ini  (경로를 각자 수정)"
echo "============================================="
