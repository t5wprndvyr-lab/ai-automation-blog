"""
最新記事のリンクを X (旧Twitter) に公式APIで告知する。
X_API_KEY 等が .env に設定されていない場合は何もせず終了する(未設定でも他の処理は壊さない)。

使い方:
    python3 scripts/post_to_x.py
"""
import os
import sys

from env_loader import load_env

load_env()

ROOT = os.path.join(os.path.dirname(__file__), "..")
POSTS_DIR = os.path.join(ROOT, "content", "posts")


def latest_post():
    files = sorted(f for f in os.listdir(POSTS_DIR) if f.endswith(".md"))
    if not files:
        return None
    path = os.path.join(POSTS_DIR, files[-1])
    with open(path, encoding="utf-8") as f:
        content = f.read()
    _, front, _ = content.split("---\n", 2)
    meta = {}
    for line in front.strip().splitlines():
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    return meta


def main():
    required = ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"]
    if not all(os.environ.get(k) for k in required):
        print("X APIキー未設定のためスキップします(.env の X_* を設定すると自動投稿されます)")
        return

    post = latest_post()
    if not post:
        print("投稿対象の記事がありません")
        return

    site_url = os.environ.get("SITE_URL", "").rstrip("/")
    link = f"{site_url}/posts/{post['slug']}.html" if site_url else ""
    text = f"新着記事: {post['title']}\n{post.get('description', '')}\n{link}".strip()
    if len(text) > 280:
        text = text[:277] + "..."

    import tweepy

    client = tweepy.Client(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_SECRET"],
    )
    resp = client.create_tweet(text=text)
    print(f"投稿完了: {resp}")


if __name__ == "__main__":
    main()
