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


_STRAY_MARKER_RE = re.compile(r"^[\-*_#]{0,6}\s*(FREE|PAID|TAGS)?\s*[\-*_#]{0,6}$")


def strip_stray_dashes(s):
    lines = s.splitlines()
    while lines and (lines[0].strip() == "" or _STRAY_MARKER_RE.match(lines[0].strip())):
        lines = lines[1:]
    while lines and (lines[-1].strip() == "" or _STRAY_MARKER_RE.match(lines[-1].strip())):
        lines = lines[:-1]
    return "\n".join(lines).strip()


_SECTION_MARKER_RE = re.compile(r"^[\-*_#\s]*\b(FREE|PAID|TAGS)\b[\-*_#:\s]*$", re.MULTILINE)


def parse_note_output(text):
    if "TITLE:" not in text:
        return None, None, None, None

    _, _, rest = text.partition("TITLE:")
    rest_lines = rest.splitlines()
    title = rest_lines[0].strip() if rest_lines else ""
    body = "\n".join(rest_lines[1:])

    # "---FREE---" 等の区切りマーカーの表記ゆれ(ダッシュの数・改行位置など)を
    # 吸収するため、マーカー行の位置で区切って各セクションを取り出す
    matches = list(_SECTION_MARKER_RE.finditer(body))
    sections = {}
    for i, m in enumerate(matches):
        key = m.group(1)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        sections[key] = strip_stray_dashes(body[start:end])

    if "FREE" in sections and "PAID" in sections:
        return title, sections["FREE"], sections["PAID"], sections.get("TAGS", "")

    return None, None, None, None


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
- 【絶対禁止】`curl ... | bash` のような、URLからインストールスクリプトを取得して
  実行するコマンドを一切書かない(実在しないURLを捏造する原因になり、読者に危険な
  操作を促すことにもなる)。インストール方法を書く必要がある場合は、具体的なURLや
  コマンドを書かず「公式サイトの案内に従ってインストールしてください」とだけ書く

# 出力形式(厳守・この形式以外の文章を加えない)
TITLE: <32文字以内。既存noteのタイトルの型を参考にする(例:「知らないと損⁉️〇〇vs〇〇
2026年〇〇はどっちだ。《徹底比較》」「〇〇したら、△△になった──最後にたどり着く
真実」のような、比較・逆説・煽り疑問形のいずれかのパターンを使う)
---FREE---
<無料公開部分。1000〜1500文字程度、複数段落。導入の語りかけ(または「結論から言う。」
のような切り込み)、なぜ今このテーマなのかの背景、「この記事を読むとわかること」の
具体的な予告(箇条書き可)を含める。最後は有料部分の中身を軽く予告して
「続きは、有料編で。」のように自然に締める>
---PAID---
<有料部分の本文をMarkdownで。2500〜4000文字程度、無料ブログには無い深さにする。
具体的な手順・テンプレート・チェックリスト・コード例を必ず含める。「## まとめ」を
最後に置く>
---TAGS---
<半角スペース区切りのハッシュタグ8〜12個。#AI #ClaudeCode #Codex #自動化 #副業
#資産形成 #新NISA #不労所得 などから今回のテーマに合うものを選び、既存アカウントの
タグの雰囲気(投資・資産形成・FIRE関連タグを必ず数個混ぜる)に合わせる>
"""


def main():
    candidates = blog_posts_without_note_draft()
    if not candidates:
        print("note化する対象のブログ記事がありません(全て生成済み、またはブログ記事が0件)")
        return

    blog_post = candidates[0]
    prompt = build_prompt(blog_post)
    text = call_llm(prompt)

    title, free_teaser, paid_body, tags = parse_note_output(text)
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
        f.write(paid_body + "\n\n")
        if tags:
            f.write("## (タグ)\n\n")
            f.write(tags + "\n")

    render_preview(slug, title, free_teaser, paid_body, tags, DEFAULT_PRICE)
    print(f"生成完了: {out_path}")
    print(f"プレビュー: docs_note_preview/{slug}.html をブラウザで開いてコピペしてください")


def render_preview(slug, title, free_teaser, paid_body, tags, price):
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
  .tags {{ margin-top: 24px; color:#2b7de9; font-size:0.9rem; }}
  pre {{ background:#1e1e2e; color:#eee; padding:10px; border-radius:6px; overflow-x:auto; }}
</style></head>
<body>
<p class="copy-hint">↓ この本文を選択してコピーし、noteの編集画面に貼り付けてください。有料エリアの区切りはnote側の「続きは購入者のみ」ボタンで設定します。</p>
<h1>{title}</h1>
<p><span class="price">想定価格: {price}円</span></p>
{free_html}
<div class="paywall">▼ ここでnoteの「続きは有料」区切りを入れる ▼</div>
{paid_html}
<p class="tags">{tags}</p>
</body></html>
"""
    os.makedirs(NOTE_PREVIEW_DIR, exist_ok=True)
    with open(os.path.join(NOTE_PREVIEW_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
        f.write(page)


if __name__ == "__main__":
    main()
