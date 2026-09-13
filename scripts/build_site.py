"""
content/posts/*.md を読み込み、docs/ 以下に静的サイトを書き出す。
GitHub Pages の Source を「main branch / docs フォルダ」に設定すればそのまま公開できる。

使い方:
    python3 scripts/build_site.py
"""
import os

import markdown

from env_loader import load_env

load_env()

ROOT = os.path.join(os.path.dirname(__file__), "..")
POSTS_DIR = os.path.join(ROOT, "content", "posts")
DOCS_DIR = os.path.join(ROOT, "docs")

SITE_TITLE = os.environ.get("SITE_TITLE", "AI活用ラボ")
SITE_URL = os.environ.get("SITE_URL", "").rstrip("/")
SITE_DESCRIPTION = os.environ.get("SITE_DESCRIPTION", "")
ADSENSE_CLIENT_ID = os.environ.get("ADSENSE_CLIENT_ID", "").strip()

ADSENSE_SNIPPET = (
    f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE_CLIENT_ID}" crossorigin="anonymous"></script>'
    if ADSENSE_CLIENT_ID
    else "<!-- AdSense未設定: .env の ADSENSE_CLIENT_ID を設定すると自動で挿入されます -->"
)

PAGE_TEMPLATE = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
{adsense}
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", sans-serif; max-width: 720px; margin: 0 auto; padding: 24px 16px 80px; line-height: 1.8; }}
  header {{ margin-bottom: 32px; }}
  header a {{ text-decoration: none; color: inherit; font-weight: 700; font-size: 1.3rem; }}
  h1 {{ font-size: 1.6rem; }}
  h2 {{ font-size: 1.25rem; margin-top: 2em; border-left: 4px solid #6366f1; padding-left: 10px; }}
  .meta {{ color: #888; font-size: 0.9rem; margin-bottom: 1.5em; }}
  .card {{ display: block; padding: 16px 0; border-bottom: 1px solid #e5e5e5; text-decoration: none; color: inherit; }}
  .card h2 {{ margin: 0 0 6px; border: none; padding: 0; font-size: 1.15rem; }}
  .card p {{ margin: 0; color: #666; font-size: 0.95rem; }}
  blockquote {{ background: #f5f5f7; border-left: 4px solid #6366f1; margin: 1.5em 0; padding: 10px 16px; border-radius: 4px; }}
  pre {{ background: #1e1e2e; color: #eee; padding: 12px; border-radius: 8px; overflow-x: auto; }}
  code {{ background: rgba(99,102,241,0.1); padding: 2px 5px; border-radius: 4px; }}
  footer {{ margin-top: 60px; color: #999; font-size: 0.85rem; text-align: center; }}
</style>
</head>
<body>
<header><a href="{home_href}">{site_title}</a></header>
{body}
<footer>&copy; {site_title}</footer>
</body>
</html>
"""


def parse_post(path):
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert content.startswith("---\n")
    _, front, body = content.split("---\n", 2)
    meta = {}
    for line in front.strip().splitlines():
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    meta["body_md"] = body.strip()
    return meta


def main():
    os.makedirs(os.path.join(DOCS_DIR, "posts"), exist_ok=True)

    posts = []
    if os.path.isdir(POSTS_DIR):
        for fname in sorted(os.listdir(POSTS_DIR), reverse=True):
            if fname.endswith(".md"):
                posts.append(parse_post(os.path.join(POSTS_DIR, fname)))

    for post in posts:
        html_body = markdown.markdown(post["body_md"], extensions=["fenced_code", "tables"])
        page = PAGE_TEMPLATE.format(
            title=f"{post['title']} | {SITE_TITLE}",
            description=post.get("description", SITE_DESCRIPTION),
            adsense=ADSENSE_SNIPPET,
            home_href="../index.html",
            site_title=SITE_TITLE,
            body=f"<h1>{post['title']}</h1><div class='meta'>{post['date']}</div>{html_body}",
        )
        out_path = os.path.join(DOCS_DIR, "posts", f"{post['slug']}.html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(page)

    cards = "\n".join(
        f'<a class="card" href="posts/{p["slug"]}.html"><h2>{p["title"]}</h2>'
        f'<p>{p.get("description", "")}</p><p class="meta">{p["date"]}</p></a>'
        for p in posts
    )
    index_page = PAGE_TEMPLATE.format(
        title=SITE_TITLE,
        description=SITE_DESCRIPTION,
        adsense=ADSENSE_SNIPPET,
        home_href="index.html",
        site_title=SITE_TITLE,
        body=f"<p>{SITE_DESCRIPTION}</p>{cards}",
    )
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_page)

    with open(os.path.join(DOCS_DIR, ".nojekyll"), "w") as f:
        f.write("")

    print(f"ビルド完了: {len(posts)}件の記事 -> docs/")


if __name__ == "__main__":
    main()
