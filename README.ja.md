# mosaic-headless

データモデルに直接書き込んで Mosaic Pro（Nextend）の WordPress サイトを構築・変更します。ビジュアルエディターも DOM 操作も使わず、すべての問い合わせに実サイトでの計測結果で答えます。

[![npm](https://img.shields.io/npm/v/mosaic-headless?style=flat-square)](https://www.npmjs.com/package/mosaic-headless)
[![License: MIT](https://img.shields.io/github/license/Moksa1123/mosaic-headless?style=flat-square)](LICENSE)

[English](README.md) · [正體中文](README.zh-TW.md) · [한국어](README.ko.md)

> これは非公式のコミュニティプロジェクトです。Mosaic Pro の開発元 Nextend が作成・承認したものではなく、Nextend とは関係ありません。Mosaic Pro はライセンスが必要なサードパーティ製ソフトウェアで、本プロジェクトには含まれていません。

## 機能

Mosaic はページを独自のデータベーステーブルに、要素 1 つにつき 1 行で保存します（`post_content` ではありません）。この skill はそのデータモデルの計測済みマップと、それを通して書き込むツールです。

- **推測せずに調べる**：`tools/mo.py` が node type・プロパティ・スタイルキー・状態の名前、値の形、置ける場所、安全かどうかを答えます。データは 134 個の node type、120 個の node プロパティ、101 個のスタイルプロパティ、60 個のスタイル状態をカバーし、Mosaic Pro 1.0.13 から抽出して実サイトで 1 つずつ計測しています。
- **中国語や口語でも引ける**：`mo.py css 內距` で padding が見つかります。用語は Mosaic 自身の正體中文（zh_TW）の表記に合わせています。
- **ページとサイトを作る**：`build_page.py` と `build_site.py` は Mosaic の REST 書き込み手順でページ仕様をコミットし、ページを壊すと計測された書き方は拒否します。
- **実際に配信されたページを確認する**：検証ツールが公開ページを Chromium で読みます（レスポンシブ規則、計算後のスタイル、メニュー、ダイアログ、スライダー、フォーム）。コミットの成功だけを信じません。
- **移行と変換**：テーマ全体のエクスポートとインポート、Mosaic のデータアップグレードの実行、Elementor ページから Mosaic への変換。

## 使う場面

サイトが Mosaic Pro で動いていて、エディターを開かずにページ、テンプレート、コンポーネント、デザイントークン、ポップアップ、メニュー、インタラクションを作成・変更したいとき、または Mosaic の設定が実際に何をするかを正確に知りたいときに使います。

他のビルダーには使いません。Elementor ページは `elementor-headless`、ブロックエディターのページは `gutenberg-headless`、SEO 記事は `rankmath-seo-wp` へ。WordPress のサイト健全性チェック、プラグイン更新、セキュリティは扱いません。

## インストール

Claude plugin（Claude Code。Claude 公式ディレクトリに掲載された後はそこからも）：

```
/plugin install mosaic-headless --marketplace Moksa1123/mosaic-headless
```

npx（Claude Code とほかの AI コーディングツール：Cursor、Codex CLI、Gemini CLI、Copilot、Continue、Windsurf、Claude.ai アップロード用 zip）：

```bash
npx mosaic-headless@latest claude-code --global --force
npx mosaic-headless --list
```

手動コピー：

```bash
git clone https://github.com/Moksa1123/mosaic-headless.git
cp -r mosaic-headless ~/.claude/skills/mosaic-headless
```

動作要件：Python 3（検索・構築・セルフテストは標準ライブラリのみ）。ブラウザー検証ツールには Playwright（`requirements.txt`）。`.php` ツールにはサーバー上の WP-CLI。Node.js は npx インストーラーにのみ必要です。Windows、macOS、Linux で動作します。npm の新しいバージョンは、`--force` を付けてインストーラーを再実行するまで反映されません。

## クイックスタート

アシスタントへの依頼の例：

- 「Mosaic サイトにランディングセクションを作って：H1、段落、/contact/ へのボタン。」
- 「Mosaic の accordion-content は div の中に直接置ける？」
- 「各ステップを閉じると次へ進む、3 ステップのポップオーバーツアーを追加して。」

自分でデータを引くこともできます：

```bash
python tools/mo.py check div text accordion-content
```

```
type               outcome     why
-----------------  ----------  -----------------------------------------------
accordion-content  BROKE_PAGE  AccordionItemElementMResource instance required
```

終了コードは 1 です。この type を単独で置くとコミットは成功しますが、公開ページ全体がエラー文字列になります。置くべき場所は `python tools/mo.py type accordion-content` が示します。

## トリガーフレーズ

English: Mosaic Pro, Nextend, build a Mosaic page without the editor, Mosaic padding / hover / breakpoint, Mosaic popup, popover, modal, Mosaic interaction, move a Mosaic theme, Mosaic upgrade, Elementor to Mosaic.

中文：Mosaic、Nextend、不開編輯器做頁面、內距、外距、圓角、懸停、斷點、RWD、彈出視窗、浮動框、摺疊面板、頁籤、輪播、互動、動畫、搬佈景、Mosaic 升級、Elementor 轉 Mosaic。

## 実行内容と接続先

- **自動では何も実行されません。** フック、MCP サーバー、バックグラウンドプロセスはありません。Claude が `SKILL.md` に従ってコマンドを提案し、あなたが承認したときだけ実行されます。
- **ローカルのみ、通信なし**：`tools/mo.py` は `data/` の CSV を読んで答えを表示します。`tools/test_mosaic.py` と `tools/check_numbers.py` はこのリポジトリを読みます。書き込みも通信もしません。
- **REST API であなたの WordPress サイトへ**：`build_page.py`、`build_site.py`、`data_upgrade.py`、`theme_zip.py`、`sweep_*.py`、`probe*.py` は、設定した 1 つのサイトの Mosaic REST ルートを呼び出し、ページ、コンポーネント、テンプレート、テーマを読み書きします。接続先はそのサイトだけです。
- **WP-CLI であなたのサイト上で実行**：`tools/*.php` は `wp eval-file` でサーバー上（通常はあなた自身の SSH 経由）の WordPress 内で動き、そのサイトの Mosaic テーブルとテーマデータを読み書きします。`theme_delete.php` と `prune_unbound.php` はデータを削除するため、`--apply` を付けない限り試行のみです。
- **公開ページの読み取り**：`tools/verify_*.py` と `audit_mobile.py` は同じサイトのページを Playwright（Chromium）または `urllib` で開き、配信結果と書き込んだ内容を比較します。
- **認証情報**：サイト URL、WordPress のログイン cookie、それに対応する `wp_rest` nonce（あなた自身のサイトの管理者のもの）。`tools/mint_session.php` がサーバー上でこれらを表示します。plugin としてインストールすると Claude Code が `userConfig` として尋ね、cookie と nonce は機密扱いでプラットフォームの資格情報ストアに保存されます。環境変数（`MOSAIC_SITE_URL`、`MOSAIC_REST_COOKIE`、`MOSAIC_REST_NONCE`）や、`--config` で渡す自分の JSON ファイルも使えます。**どのツールもあなたのマシン上で認証情報を探しません。**
- **第三者**：`sites/` の作例は Google Fonts を読み込むため、それで作ったページでは訪問者のブラウザーが Google からフォントを取得します。
- インストール時に何もダウンロードせず、作者や第三者にデータを送りません。

## 検証方法

- node type、node プロパティ、スタイルプロパティ、スタイル状態はプラグインのソースから抽出し（`tools/check_tables.py` が再抽出して差分を確認）、実サイトに 1 つずつ書き込んで、配信された HTML とコンパイル後の CSS で確認しています。
- デモページを Chromium で読み直し、733 件のレスポンシブ宣言を実際に配信されたスタイルシートと照合し、3 つの画面幅で 4,132 件の計算後スタイルを取得しました。詳細：[verification-record.md](references/verification-record.md)。
- セルフテスト：`python tools/test_mosaic.py`、オフラインの 42 項目（検索、中国語の用語、構築結果の形と拒否ルール、公開されている構築インターフェース、このリポジトリの数値とプライバシー）。
- evals：Mosaic 1.0.10〜1.0.12 の挙動に関する 16 問。skill ありで 16/16、なしで 0/16。結果：[evals/RESULTS.md](evals/RESULTS.md)。
- `SKILL.md` とこれらの README の数値は、`tools/check_numbers.py` がデータと照合しています。

## 制限

- Mosaic Pro 1.0.13 まで計測済みです。1.0.13 のエディターにしかない機能（新しいスタイル変数の種類、List のクラス、pageLoad の遅延など）はまだ計測しておらず、ツールも書き込みません。
- グリッド子要素の配置プロパティは headless で書き込んでも出力されません。一部のインタラクションの形はまだ計測していません。
- ブラウザー検証ツールには Playwright と書き込み可能なサイトが必要で、オフラインのセルフテストには含まれません。
- 未解決の項目：[data/pending.csv](data/pending.csv)。詳しいガイド（失敗モード、トークンコスト、Elementor 変換、作例）：[docs/guide.md](docs/guide.md)（英語）。

## リポジトリ構成

```
SKILL.md          アシスタントが読み込む内容：出典、ルーティング、作業、検証
data/             計測済みテーブル（CSV）、中国語の用語、未解決リスト
references/       トピック別ガイド：データモデル、スタイル、ダイアログ、アップグレード…
tools/            mo.py、構築・検証ツール、WP-CLI スクリプト、セルフテスト
sites/            作例（読める Python モジュール）
evals/            採点用の問題と結果
scripts/          インストーラーとリリースゲート
assets/           プラットフォーム別のインストールテンプレート
docs/             詳しいガイド
.claude-plugin/   plugin と marketplace のマニフェスト
```

## ライセンスと作者

MIT License。作者 Moksa（[moksaweb.com](https://moksaweb.com)）。問題の報告：[GitHub](https://github.com/Moksa1123/mosaic-headless/issues)。
