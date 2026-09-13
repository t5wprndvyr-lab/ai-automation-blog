"""記事生成スクリプト共通のLLM呼び出し。LLM_PROVIDER=ollama(デフォルト・無料) / anthropic(有料)。"""
import json
import os
import sys
import urllib.error
import urllib.request

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "ollama").strip().lower()
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b-instruct")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

FACT_GUARDRAILS = """# 事実として必ず守ること(誤りを書かない)
- Claude Code は Anthropic 社が開発したAIコーディングツールである(OpenAI製ではない)
- Codex は OpenAI が開発したAIコーディングツールである(Anthropic製ではない)
- 上記2つは別々の会社の別々の製品であり、混同して説明しない
- 存在しないAPI名・存在しないコマンド・架空のライブラリ名を作らない。具体例を挙げる際は
  一般的で実在するもの(Python標準ライブラリ、bash、gitコマンドなど)に留める"""

LANGUAGE_GUARDRAILS = (
    "重要: 必ず日本語のみで出力してください。中国語(簡体字・繁体字)や英語の文章を混ぜる"
    "ことは禁止です。すべての文・見出し・説明を日本語で書いてください。"
)


def call_ollama(prompt):
    payload = json.dumps({"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/generate", data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read())
    except urllib.error.URLError as e:
        print(
            f"ERROR: Ollamaに接続できません({e})。`ollama serve` が起動しているか確認してください。",
            file=sys.stderr,
        )
        sys.exit(1)
    return data["response"].strip()


def call_anthropic(prompt):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY が設定されていません。.env を確認してください。", file=sys.stderr)
        sys.exit(1)

    from anthropic import Anthropic

    client = Anthropic(api_key=api_key)
    resp = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text.strip()


def call_llm(prompt):
    if LLM_PROVIDER == "anthropic":
        return call_anthropic(prompt)
    return call_ollama(prompt)


def parse_title_description_body(text):
    """`TITLE: ...` / `DESCRIPTION: ...` / 本文 という形式のLLM出力をパースする。"""
    lines = [l for l in text.splitlines() if l.strip() != ""]
    if not lines or not lines[0].startswith("TITLE:"):
        return None, None, None

    title = lines[0].split(":", 1)[1].strip()
    description = ""
    body_start = 1
    if len(lines) > 1 and lines[1].startswith("DESCRIPTION:"):
        description = lines[1].split(":", 1)[1].strip()
        body_start = 2
    body = "\n".join(lines[body_start:]).strip()
    return title, description, body
