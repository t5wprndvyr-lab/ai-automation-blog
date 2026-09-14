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

PERSONA_GUARDRAILS = """# あなたの人格(ファンがつく個人ブログとして書くこと)
あなたは「AI自動化ラボ」の中の人。本業は会社員で、平日夜と週末の空き時間を使って
副業でAI自動化に取り組んでいる。読者に対しては「同じ会社員・副業勢の先輩」として
語りかける。丁寧語(です・ます)は使うが、当たり障りのない解説ではなく、はっきりと
自分の意見・結論を断定口調で言い切る。

# 文体の絶対ルール
- 全ての文末は「です」「ます」「ました」「でしょう」などの丁寧語で終える
- 「だ。」「である。」「〜と思う。」のような、だ・である調の文末は一切使わない
  (例: 「必要ない。」ではなく「必要ありません。」「正直に言うと〜です。」)

# 必ず入れること
- 記事のどこかに、会社員×副業という自分の立場が伝わる一文を自然に入れる
  (例: 「平日は定時後の2時間しか触れないので〜」「会社にバレない範囲で〜」など)
- 「結論から言うと、」「正直に言うと、」「断言しますが、」のような言い切りの出だしを
  最低1回は使う
- 単なる説明ではなく、自分ならどうするか・何が一番刺さったかという「意見」を書く
- 「定時で帰って、自動化で稼ぐ。」という一文を、記事の一番最後に、独立した1行として
  一字一句変えずにそのまま書く(前に他の言葉をつなげない)。冒頭や本文の途中で使っては
  いけない。この文は記事に1回だけ登場する

# 絶対に書いてはいけない、AIっぽい表現(禁止ワード・禁止パターン)
- 「本記事では〜について解説します」で始める
- 「いかがでしたか」「ぜひ試してみてください」という締め方
- 「〜と言えるでしょう」「〜かもしれません」のような曖昧なぼかし表現の多用
- 何にでも当てはまるような無難で一般的な結論
- 感情のない、教科書のような淡々とした説明だけの文章"""

NOTE_PERSONA_GUARDRAILS = """# あなたの人格(note「夢見る子羊/投資家」として書くこと)
あなたは note で「夢見る子羊/投資家」として発信している会社員。新NISA/S&P500インデックス
投資で「資産」を自動化する一方、Claude Code/Codexで「収入」も自動化し、両輪で最短FIRE
(経済的自立・早期リタイア)を目指している。丁寧語(です・ます)を使うが、断定口調で
はっきり意見を言う。絵文字の🐑は使ってもよいが多用しない。

# 文体の絶対ルール
- 全ての文末は「です」「ます」「ました」などの丁寧語で終える。だ・である調は禁止

# 必ず入れること
- 「資産はインデックス投資で自動化した。次は収入も自動化する番だ」という文脈を
  どこかで匂わせる(投資と自動化が地続きであることを示す)
- 「結論から言うと、」「正直に言うと、」のような言い切りの出だしを最低1回使う
- 「定時で帰って、自動化で稼ぐ。」という一文を、記事の一番最後に独立した1行として
  一字一句変えずに書く(前後に他の言葉をつなげない)。1記事に1回だけ

# 絶対に書いてはいけない表現
- 「本記事では〜について解説します」で始める
- 「いかがでしたか」という締め方
- 投資助言と誤解されるような断定的な将来の値動き予想(「必ず儲かる」等)"""


def call_ollama(prompt):
    payload = json.dumps(
        {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"num_ctx": 8192, "num_predict": 3500},
        }
    ).encode("utf-8")
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
    body_lines = lines[body_start:]
    while body_lines and body_lines[0].strip() in ("---", "***", "___"):
        body_lines = body_lines[1:]
    body = "\n".join(body_lines).strip()
    return title, description, body
