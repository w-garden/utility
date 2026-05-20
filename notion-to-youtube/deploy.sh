#!/usr/bin/env bash
set -e

# .env.deploy 파일이 있으면 로드
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ -f "$SCRIPT_DIR/.env.deploy" ]]; then
  # shellcheck disable=SC1091
  set -a; source "$SCRIPT_DIR/.env.deploy"; set +a
fi

: "${APP_PASSWORD:?APP_PASSWORD 환경변수가 필요합니다}"
: "${GITHUB_PAT:?GITHUB_PAT 환경변수가 필요합니다}"
: "${NOTION_TOKEN:?NOTION_TOKEN 환경변수가 필요합니다}"

sam deploy \
  --stack-name notion-youtube-sync \
  --s3-bucket aws-sam-cli-managed-default-samclisourcebucket-h7hjf7rlxmjl \
  --region ap-northeast-2 \
  --capabilities CAPABILITY_IAM \
  --no-confirm-changeset \
  --parameter-overrides \
    GistId=e6d7c030aaaa3c6098f6ef1787bfe4c3 \
    PlaylistId=PL6TgjrcGl62fCnYllJ8zyFLrCuv7bu3oM \
    AppPassword="$APP_PASSWORD" \
    GithubPat="$GITHUB_PAT" \
    NotionToken="$NOTION_TOKEN"
