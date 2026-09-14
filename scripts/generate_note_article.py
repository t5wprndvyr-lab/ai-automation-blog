"""
公開済みのブログ記事(content/posts/)を1本選び、その「実践的な深掘り版」を
note有料記事の原稿として生成する。note には公式投稿APIが無いため、
ここで作るのはコピー&ペーストで貼り付けられる原稿まで(投稿自体は手動)。

出力:
    content/note_drafts/<slug>.md   … フロントマター付き原稿(無料部分+有料部分)
    docs_note_preview/<slug>.html   … コピペしやすい整形済みプレビュー(git管理外)

使い方:
    python3 scripts/generate_note_article.py
"""
import datetime
import os
import re
import sys

from env_loader import load_env

load_env()

from llm import FACT_GUARDRAILS, LANGUAGE_GUARDRAILS, NOTE_PERSONA_GUARDRAILS, call_llm  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
POSTS_DIR = os.path.join(ROOT, "content", "posts")
NOTE_DRAFTS_DIR = os.path.join(ROOT, "content", "note_drafts")
NOTE_PREVIEW_DIR = os.path.join(ROOT, "docs_note_preview")

DEFAULT_PRICE = os.environ.get("NOTE_PRICE", "500")


def parse_frontmatter(path):
    with open(path, encoding="utf-8") as f:
        content = f.read()
    _, front, _ = content.split("---\n", 2)
    meta = {}
    for line in front.strip().splitlines():
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    return meta


def blog_posts_without_note_draft():
    if not os.path.isdir(POSTS_DIR):
        return []
    existing_slugs = set()
    if os.path.isdir(NOTE_DRAFTS_DIR):
        existing_slugs = {f[:-3] for f in os.listdir(NOTE_DRAFTS_DIR) if f.endswith(".md")}

    candidates = []
    for fname in sorted(os.listdir(POSTS_DIR)):
        if not fname.endswith(".md"):
            continue
        slug = fname[:-3]
        if slug in existing_slugs:
            continue
        candidates.append(parse_frontmatter(os.path.join(POSTS_DIR, fname)))
    return candidates


def parse_note_output(text):
    if "TITLE:" not in text:
        return None, None, None

    title_part, _, rest = text.partition("TITLE:")
    title = rest.splitlines()[0].strip() if rest else ""
    body = rest[len(title):].strip() if rest else ""
    # 最初の改行より後ろを本文として扱う(念のためtitle行を取り除く)
    body = "\n".join(rest.splitlines()[1:]).strip()

    if "---FREE---" in body and "---PAID---" in body:
        free_part, paid_part = body.split("---FREE---", 1)[1].split("---PAID---", 1)
        return title, free_part.strip(), paid_part.strip()

    # フォールバック: 素の "---" 区切りが2箇所以上あれば、最初の区切りまでを無料部分、
    # それ以降を有料部分として扱う
    parts = [p.strip() for p in re.split(r"^-{3,}$", body, flags=re.MULTILINE) if p.strip()]
    if len(parts) >= 2:
        return title, parts[0], "\n\n".join(parts[1:])

    return None, None, None


def slugify(title, date_str):
    ascii_part = re.sub(r"[^a-zA-Z0-9]+", "-", title).strip("-").lower()
    if not ascii_part:
        ascii_part = "note"
    return f"{date_str}-{ascii_part[:40]}"


def build_prompt(blog_post):
    return f"""{LANGUAGE_GUARDRAILS}

あなたは「AI・Codex・Claude活用術」を発信するnoteクリエイターです。
無料ブログで公開済みの以下の入門記事をベースに、有料note記事として「もっと実践的で
具体的な深掘り版」を書いてください。単なる要約ではなく、テンプレート・チェックリスト・
手順など、お金を払う価値のある実用的な内容にしてください。

{NOTE_PERSONA_GUARDRAILS}

# ベースとなった無料ブログ記事
タイトル: {blog_post.get('title', '')}
要約: {blog_post.get('description', '')}

{FACT_GUARDRAILS}

# コード例に関する厳格なルール(有料コンテンツのため絶対厳守)
- `from claude import Claude` のような架空のPython SDK/パッケージを絶対に作らない
- Claude Code、Codexには専用のpipパッケージは存在しない。コード例は「ターミナルで
  claude や codex コマンドを直接叩く」「シェルスクリプトから呼び出す」など、実際に
  存在する使い方(CLIコマンド・シェルスクリプト)のみに限定する
- 具体的なコマンド例を書く場合は `claude "プロンプト"` のような一般的なCLI呼び出しの
  形にとどめ、細かいオプション名や架空の関数名を断定的に書かない
- 自信が持てない技術的詳細は、具体的なコマンド例ではなく「手順」や「考え方」として説明する

# 出力形式(厳守・この形式以外の文章を加えない)
TITLE: <32文字以内、購買意欲を刺激する日本語タイトル>
---FREE---
<購入を迷っている読者向けの無料試し読み部分。3〜5文。何が得られるか具体的に予告し、
最後は続きが気になる一文で終える>
---PAID---
<有料部分の本文をMarkdownで。1500〜2500文字程度。具体的な手順・テンプレート・
チェックリスト・コード例を必ず含め、無料ブログには無い実践的な情報にする。
「## まとめ」を置いた後、PERSONA_GUARDRAILSで指定された締めの一文を書く>
"""


def main():
    candidates = blog_posts_without_note_draft()
    if not candidates:
        print("note化する対象のブログ記事がありません(全て生成済み、またはブログ記事が0件)")
        return

    blog_post = candidates[0]
    prompt = build_prompt(blog_post)
    text = call_llm(prompt)

    title, free_teaser, paid_body = parse_note_output(text)
    if title is None:
        print("ERROR: 期待した出力形式ではありません:\n" + text[:500], file=sys.stderr)
        sys.exit(1)

    date_str = datetime.date.today().isoformat()
    slug = slugify(title, date_str)

    os.makedirs(NOTE_DRAFTS_DIR, exist_ok=True)
    out_path = os.path.join(NOTE_DRAFTS_DIR, f"{slug}.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("---\n")
        f.write(f"title: {title}\n")
        f.write(f"date: {date_str}\n")
        f.write(f"price: {DEFAULT_PRICE}\n")
        f.write(f"based_on: {blog_post.get('slug', '')}\n")
        f.write("---\n\n")
        f.write("## (無料公開部分)\n\n")
        f.write(free_teaser + "\n\n")
        f.write("## (ここから有料)\n\n")
        f.write(paid_body + "\n")

    render_preview(slug, title, free_teaser, paid_body, DEFAULT_PRICE)
    print(f"生成完了: {out_path}")
    print(f"プレビュー: docs_note_preview/{slug}.html をブラウザで開いてコピペしてください")


def render_preview(slug, title, free_teaser, paid_body, price):
    import markdown

    free_html = markdown.markdown(free_teaser)
    paid_html = markdown.markdown(paid_body, extensions=["fenced_code"])

    page = f"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<title>{title}(noteプレビュー)</title>
<style>
  body {{ font-family: -apple-system, "Hiragino Sans", sans-serif; max-width: 680px; margin: 40px auto; line-height: 1.9; padding: 0 16px; }}
  h1 {{ font-size: 1.4rem; }}
  .price {{ display:inline-block; background:#41c9b4; color:#fff; padding:4px 12px; border-radius:6px; font-size:0.9rem; }}
  .paywall {{ margin: 32px 0; padding: 14px; background:#fff6de; border:1px dashed #e0a800; border-radius:8px; font-size:0.9rem; }}
  .copy-hint {{ color:#888; font-size:0.85rem; }}
  pre {{ background:#1e1e2e; color:#eee; padding:10px; border-radius:6px; overflow-x:auto; }}
</style></head>
<body>
<p class="copy-hint">↓ この本文を選択してコピーし、noteの編集画面に貼り付けてください。有料エリアの区切りはnote側の「続きは購入者のみ」ボタンで設定します。</p>
<h1>{title}</h1>
<p><span class="price">想定価格: {price}円</span></p>
{free_html}
<div class="paywall">▼ ここでnoteの「続きは有料」区切りを入れる ▼</div>
{paid_html}
</body></html>
"""
    os.makedirs(NOTE_PREVIEW_DIR, exist_ok=True)
    with open(os.path.join(NOTE_PREVIEW_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
        f.write(page)


if __name__ == "__main__":
    main()
