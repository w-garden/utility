#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ -f "$SCRIPT_DIR/.env.deploy" ]]; then
  set -a; source "$SCRIPT_DIR/.env.deploy"; set +a
fi

: "${APP_PASSWORD:?APP_PASSWORD 환경변수가 필요합니다}"

sam deploy \
  --stack-name pptx-updater \
  --s3-bucket aws-sam-cli-managed-default-samclisourcebucket-h7hjf7rlxmjl \
  --s3-prefix pptx-updater \
  --region ap-northeast-2 \
  --capabilities CAPABILITY_IAM \
  --no-confirm-changeset \
  --no-fail-on-empty-changeset \
  --parameter-overrides AppPassword="$APP_PASSWORD"
