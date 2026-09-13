"""
LLMで「AI・Codex・Claude活用術」ニッチの新規記事を1本生成し、
content/posts/ に Markdown (簡易フロントマター付き) として保存する。

LLM_PROVIDER=ollama (デフォルト・無料・要 `ollama serve` 起動中) か
LLM_PROVIDER=anthropic (要 ANTHROPIC_API_KEY・従量課金) を .env で切り替え可能。

使い方:
    python3 scripts/generate_post.py
"""
import datetime
import os
import re
import sys

from env_loader import load_env

load_env()

from llm import (  # noqa: E402
    FACT_GUARDRAILS,
    LANGUAGE_GUARDRAILS,
    PERSONA_GUARDRAILS,
    call_llm,
    parse_title_description_body,
)

POSTS_DIR = os.path.join(os.path.dirname(__file__), "..", "content", "posts")

TOPIC_ANGLES = [
    "Claude CodeとCodexの使い分け方",
    "個人開発の自動化レシピ",
    "業務効率化の具体的な自動化事例",
    "プロンプト設計のコツ",
    "AIコーディングでハマりやすい失敗と対策",
    "副業・受託案件で使えるAI自動化テクニック",
    "MacでのAI開発環境構築",
    "自動化スクリプトのセキュリティ・注意点",
    "AIツール同士の連携(MCP・API連携)",
    "AI活用で時間を生み出す働き方の実例",
]


def existing_titles():
    titles = []
    if not os.path.isdir(POSTS_DIR):
        return titles
    for fname in os.listdir(POSTS_DIR):
        if not fname.endswith(".md"):
            continue
        with open(os.path.join(POSTS_DIR, fname), encoding="utf-8") as f:
            for line in f:
                if line.startswith("title:"):
                    titles.append(line.split(":", 1)[1].strip())
                    break
    return titles


def slugify(title, date_str):
    ascii_part = re.sub(r"[^a-zA-Z0-9]+", "-", title).strip("-").lower()
    if not ascii_part:
        ascii_part = "post"
    return f"{date_str}-{ascii_part[:40]}"


def build_prompt(avoid_titles, angle):
    avoid_block = "\n".join(f"- {t}" for t in avoid_titles[-30:]) or "(まだ記事はありません)"
    return f"""{LANGUAGE_GUARDRAILS}

あなたは「AI・Codex・Claude活用術」を発信する個人ブログの執筆者です。
読者は個人開発者・フリーランスエンジニア・業務効率化に関心がある会社員です。

{PERSONA_GUARDRAILS}

{FACT_GUARDRAILS}

今回の切り口: {angle}

# 既存記事タイトル(重複禁止)
{avoid_block}

# 出力形式(厳守・他の文章を一切加えない)
1行目: TITLE: <32文字以内の日本語タイトル>
2行目: DESCRIPTION: <80文字以内の日本語要約>
3行目: 空行
4行目以降: 本文をMarkdownの日本語で。(空行を挟まず1行目からTITLE:で始めること)

# 本文の要件
- 1200〜1800文字程度の日本語記事
- 具体的な手順・コード例・チェックリストなど実用的な内容を必ず含める
- 見出し(##)を3〜5個使い読みやすく構成する
- 誇大な釣り表現や断定しすぎる医療/金融アドバイスは避ける
- 「## まとめ」を置いた後、PERSONA_GUARDRAILSで指定された締めの一文を書く
- 本文の最後に独立した1行として `{{{{CTA}}}}` というプレースホルダーを追記する(これは後処理で置換されるので変更しないこと)
"""


def main():
    titles = existing_titles()
    angle = TOPIC_ANGLES[len(titles) % len(TOPIC_ANGLES)]
    prompt = build_prompt(titles, angle)

    text = call_llm(prompt)
    title, description, body = parse_title_description_body(text)
    if title is None:
        print("ERROR: 期待した出力形式ではありません:\n" + text[:500], file=sys.stderr)
        sys.exit(1)

    contact_url = os.environ.get("CONTACT_URL", "").strip()
    cta_text = (
        f"\n\n> 自社の業務自動化・AI導入のご相談はお気軽にどうぞ → [{contact_url}]({contact_url})\n"
        if contact_url
        else ""
    )
    body = body.replace("{{CTA}}", cta_text.strip())

    date_str = datetime.date.today().isoformat()
    slug = slugify(title, date_str)

    os.makedirs(POSTS_DIR, exist_ok=True)
    out_path = os.path.join(POSTS_DIR, f"{slug}.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("---\n")
        f.write(f"title: {title}\n")
        f.write(f"date: {date_str}\n")
        f.write(f"description: {description}\n")
        f.write(f"slug: {slug}\n")
        f.write("---\n\n")
        f.write(body + "\n")

    print(f"生成完了: {out_path}")


if __name__ == "__main__":
    main()
