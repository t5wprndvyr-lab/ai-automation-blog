#!/bin/bash
# 記事生成 -> サイトビルド -> git push -> X告知 を一括実行する。
set -euo pipefail
cd "$(dirname "$0")/.."

source .venv/bin/activate
export PATH="$HOME/opt/ollama-cli:$PATH"

if ! curl -s -o /dev/null http://localhost:11434/api/version; then
  ollama serve >> logs/ollama.log 2>&1 &
  sleep 3
fi

python3 scripts/generate_post.py
python3 scripts/build_site.py

if git remote get-url origin >/dev/null 2>&1; then
  git add content/ docs/
  git commit -m "chore: 記事を自動追加 ($(date +%F))" || echo "コミットする変更がありません"
  git push
else
  echo "git remote 'origin' が未設定のため push をスキップしました"
fi

python3 scripts/post_to_x.py
