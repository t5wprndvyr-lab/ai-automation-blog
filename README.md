# AI・Codex・Claude活用ラボ (自動化ブログ基盤)

LLM(無料のローカルOllama、または有料のClaude API)で記事を自動生成 → 静的サイトにビルド → GitHub Pagesで公開 → (任意)Xに告知、まで無人で回すパイプラインです。
このリポジトリ自体を「AI自動化構築サービス」の実績デモとしても使えます。

**公開中のサイト**: https://t5wprndvyr-lab.github.io/ai-automation-blog/
**リポジトリ**: https://github.com/t5wprndvyr-lab/ai-automation-blog

## 構成

```
content/posts/*.md          生成されたブログ記事(無料公開・Markdown)
content/note_drafts/*.md    生成されたnote有料記事の下書き(git管理外・要レビュー)
docs/                       ビルド後の静的サイト(GitHub Pagesの公開元)
docs_note_preview/          noteへのコピペ用プレビューHTML(git管理外)
scripts/llm.py               Ollama/Anthropic共通のLLM呼び出し
scripts/generate_post.py     ブログ記事を1本生成(デフォルト: 無料のOllama)
scripts/generate_note_article.py  ブログ記事の深掘り版をnote有料原稿として生成
scripts/build_site.py        Markdown -> HTML変換・サイト生成
scripts/post_to_x.py         最新記事をXに告知(公式API・任意)
scripts/publish.sh            上記を一括実行 + git push
launchd/                     macOSで毎日自動実行するための設定
```

## セットアップ手順

### 1. 依存関係・記事生成エンジン(済み)
`.venv` に `anthropic` / `markdown` / `tweepy` をインストール済みです。
記事生成は**無料のローカルLLM(Ollama + Qwen2.5 7B)**をデフォルトで使用します(`~/opt/ollama-cli` に導入済み)。
Claude APIの方が文章品質は上ですが従量課金のため、クレジットを追加した場合は `.env` の `LLM_PROVIDER=anthropic` に切り替えれば使えます。

### 2. .env の確認
`.env` は作成済みです(GitHub Pages公開URLも設定済み)。中身を変えたい場合のみ編集してください。

### 3. 動作確認(1本手動生成)
```bash
export PATH="$HOME/opt/ollama-cli:$PATH"
ollama serve &        # 既に起動していれば不要
source .venv/bin/activate
cd scripts
python3 generate_post.py   # 新しい記事が content/posts/ に生成される
python3 build_site.py      # docs/ に静的サイトが生成される
```

### 4. GitHubリポジトリ・Pages公開(完了済み)
リポジトリ作成・push・GitHub Pages設定は完了しています。今後の更新は `git push` するだけで数分後にサイトへ反映されます。

### 5. 毎日自動実行する(macOS launchd)
```bash
cp launchd/com.yoshi.aiblog.publish.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.yoshi.aiblog.publish.plist
```
毎朝8:00に `scripts/publish.sh`(記事生成 → ビルド → push → X告知)が自動実行されます。
止めたい場合は `launchctl unload ~/Library/LaunchAgents/com.yoshi.aiblog.publish.plist`。

### 6. (任意) Xへの自動告知
https://developer.x.com/ でDeveloperアカウント登録 → Appを作成 → API Key/Secret、Access Token/Secretを取得し `.env` に設定。
**無料枠でも月500件までWrite(投稿)が可能**です。非公式手段(スクレイピング等)での自動投稿はアカウント凍結リスクがあるため使用しないでください。

### 7. note有料販売(半自動)
noteには外部からの自動投稿API自体が存在しないため、投稿ボタンを押す作業だけは手動です。
それ以外は自動化しています。

```bash
python3 scripts/generate_note_article.py
```
- 公開済みのブログ記事を1本選び、その「実践的な深掘り版」を有料note原稿として生成
- `content/note_drafts/<slug>.md` に無料試し読み部分+有料部分を保存(**gitには含めません**。
  有料コンテンツを公開リポジトリにpushすると誰でも無料で読めてしまうため)
- `docs_note_preview/<slug>.html` にコピペしやすい整形済みプレビューを生成(こちらもgit管理外)

**投稿前に必ずやること(無料モデル特有の癖のため重要)**
- コード例が実在するコマンド/ライブラリか確認する(架空のpipパッケージ等を生成することがあります)
- 会社名・製品名などの事実関係を確認する
- 変な日本語・言語混入がないか確認する

問題なければ `docs_note_preview/<slug>.html` をブラウザで開いて全選択コピーし、
note.comの新規記事作成画面に貼り付け、note標準の「続きは購入者のみ」機能で
有料エリアの区切りを設定して公開します。`publish.sh` にも組み込み済みなので、
毎日の自動実行のたびに下書きが1本ずつ溜まっていきます。

### 8. 収益化の設定
- **Google AdSense**: サイトに数記事たまってから https://www.google.com/adsense/ に申請 → 承認後、発行された `ca-pub-XXXX` を `.env` の `ADSENSE_CLIENT_ID` に設定して再ビルド
- **アフィリエイト**: Amazonアソシエイト・A8.net等で商品リンクを取得し、`scripts/generate_post.py` のプロンプトや個別記事に手動で埋め込む
- **受託営業**: `CONTACT_URL` に自分のポートフォリオ/問い合わせページを設定すると、各記事の末尾に自動でCTAが挿入されます

## 受託(フリーランス)側の使い方

このリポジトリと公開サイトは、そのまま「SNS・コンテンツ自動化構築」サービスの実績として使えます。
- クラウドワークス/ランサーズ/Fiverrのプロフィールに、公開したサイトのURLとこのGitHubリポジトリを掲載
- 「Claude Code / Codexを使ったAI業務自動化構築、承ります」という訴求で出品
- 提案文テンプレートは別途アーティファクトとして作成済みです

## 注意事項

- `.env` は絶対にGitにコミットしないでください(`.gitignore`済み)
- SNS自動投稿は必ず公式APIの範囲内で行うこと(非公式手段は規約違反・凍結リスク)
- AdSense申請には独自ドメインの利用や一定のコンテンツ量が推奨されます(GitHub Pagesのデフォルトドメインのままでも申請自体は可能ですが、審査通過率を上げたい場合は独自ドメイン取得を検討してください)
