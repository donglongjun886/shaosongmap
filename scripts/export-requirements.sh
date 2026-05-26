#!/usr/bin/env bash
# 从 uv.lock 导出 requirements.txt，供 Docker 构建使用
set -euo pipefail

cd "$(dirname "$0")/.."

echo "正在从 uv.lock 导出 requirements.txt..."
uv export --format requirements-txt --no-hashes --no-dev --output-file requirements.txt

echo "requirements.txt 已更新"
