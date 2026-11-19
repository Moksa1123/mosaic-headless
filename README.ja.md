<h1 align="center">Mosaic Headless</h1>

<h3 align="center">Mosaic Pro 無編輯器建站工具</h3>

<p align="center">
  <strong>計測済みデータモデル · ガード付きページビルダー · 配信ページの検証</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3-blue?style=flat-square&logo=python&logoColor=white" alt="Python 3">
  <img src="https://img.shields.io/badge/node-18_or_later-green?style=flat-square&logo=node.js&logoColor=white" alt="Node.js 18 以上">
  <img src="https://img.shields.io/badge/playwright-browser_verifiers-blueviolet?style=flat-square" alt="ブラウザー検証に Playwright">
  <img src="https://img.shields.io/badge/WP--CLI-server_scripts-blue?style=flat-square&logo=wordpress&logoColor=white" alt="サーバースクリプトに WP-CLI">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/node_types-134-success?style=flat-square" alt="134 個の node type">
  <img src="https://img.shields.io/badge/node_properties-120-success?style=flat-square" alt="120 個の node プロパティ">
  <img src="https://img.shields.io/badge/style_properties-101-success?style=flat-square" alt="101 個のスタイルプロパティ">
  <img src="https://img.shields.io/badge/responsive_checks-733-blueviolet?style=flat-square" alt="733 件のレスポンシブ検査">
  <img src="https://img.shields.io/badge/self--tests-43-blueviolet?style=flat-square" alt="43 項目のセルフテスト">
</p>

<p align="center">
  <a href="https://www.npmjs.com/package/mosaic-headless"><img src="https://img.shields.io/npm/v/mosaic-headless?style=flat-square&logo=npm" alt="npm バージョン"></a>
  <a href="https://www.npmjs.com/package/mosaic-headless"><img src="https://img.shields.io/npm/dt/mosaic-headless?style=flat-square&label=downloads&color=cb3837" alt="npm ダウンロード数"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/Moksa1123/mosaic-headless?style=flat-square" alt="License"></a>
</p>

<p align="center"><a href="README.md">English</a> · <a href="README.zh-TW.md">正體中文</a> · <strong>日本語</strong> · <a href="README.ko.md">한국어</a></p>

> これは非公式のコミュニティプロジェクトです。Mosaic Pro の開発元 Nextend が作成・承認したものではなく、Nextend とは関係ありません。Mosaic Pro はライセンスが必要なサードパーティ製ソフトウェアで、本プロジェクトには含まれていません。

## 機能

Mosaic はページを独自のデータベーステーブルに、要素 1 つにつき 1 行で保存します（`post_content` ではありません）。この skill はそのデータモデルの計測済みマップと、それを通して書き込むツールです。データは Mosaic Pro 1.0.13 から抽出し、実サイトで 1 つずつ計測しています。

| 分野 | 内容 |
|---|---|
| 検索 | `tools/mo.py`：134 個の node type、120 個の node プロパティ、101 個のスタイルプロパティ、60 個のスタイル状態。それぞれ計測結果付きで答えます。中国語や口語でも引けます（`mo.py css 內距`） |
| 構築 | `build_page.py`／`build_site.py` は Mosaic の REST 書き込み手順でページ仕様をコミットし、ページを壊すと計測された書き方は拒否します |
| 検証 | 配信されたページを Chromium で読みます：レスポンシブ規則、計算後のスタイル、メニュー、ダイアログ、スライダー、フォーム |
| 移行 | テーマ全体のエクスポートとインポート、wp-admin の外からの Mosaic データアップグレード |
| 変換 | Elementor ページを Mosaic の仕様に変換し、変換できない要素はすべて名前を挙げます |

### 書く前に調べる

```bash
python tools/mo.py type accordion-content   # one type, joined to every live sweep
python tools/mo.py css 內距                  # Chinese works: padding-top/right/bottom/left
python tools/mo.py facts section padding     # measured front-end behaviour
```

### ガードを通して構築する

```bash
python tools/mo.py skeleton > page.json
python tools/build_page.py --spec page.json   # refuses unsafe types, bad placement, out-of-enum values
```

### 訪問者が受け取るページを確認する

```bash
python tools/verify_rwd.py --site page.json       # every _t/_m declaration in the served stylesheet
python tools/verify_browser.py --site page.json   # what Chromium computes, plus a design audit
```

## 使う場面

サイトが Mosaic Pro で動いていて、エディターを開かずにページ、テンプレート、コンポーネント、デザイントークン、ポップアップ、メニュー、インタラクションを作成・変更したいとき、または Mosaic の設定が実際に何をするかを正確に知りたいときに使います。

| 依頼 | 担当 |
|---|---|
| Elementor ページ | `elementor-headless` |
| ブロックエディター（Gutenberg）のページ | `gutenberg-headless` |
| SEO 記事、Rank Math のスコア | `rankmath-seo-wp` |
| サイト健全性チェック、プラグイン更新、セキュリティ | 対象外 |

## インストール

### Step 1: インストール方法を選ぶ

Claude plugin（Claude Code。Claude 公式ディレクトリに掲載された後はそこからも）：

```
/plugin install mosaic-headless --marketplace Moksa1123/mosaic-headless
```

npx（Claude Code とほかの AI コーディングツール）：

```bash
npx mosaic-headless@latest claude-code --global --force
npx mosaic-headless --list
```

手動コピー：

```bash
git clone https://github.com/Moksa1123/mosaic-headless.git
cp -r mosaic-headless ~/.claude/skills/mosaic-headless
```

| プラットフォーム | インストール内容 | 場所 |
|---|---|---|
| Claude Code | skill 一式：SKILL.md、references、tools、data、sites、evals、scripts | `~/.claude/skills/` または `./.claude/skills/` |
| Codex CLI | skill 一式 | `~/.codex/skills/` |
| Gemini CLI | skill 一式 | `~/.gemini/skills/` |
| GitHub Copilot | skill 一式 | `./.github/skills/` |
| Cursor | references を埋め込んだ `.mdc` ルール 1 つ | `~/.cursor/rules/` |
| Windsurf | references を埋め込んだルールファイル 1 つ | `./.devin/rules/` |
| Continue | references を埋め込んだルールファイル 1 つ | `~/.continue/rules/` |
| Claude.ai | アップロード用 zip（SKILL.md、references、data、sites。ツールなし） | 保存した場所 |

動作要件：Python 3（検索・構築・セルフテストは標準ライブラリのみ）。ブラウザー検証ツールには Playwright（`requirements.txt`）。`.php` ツールにはサーバー上の WP-CLI。npx インストーラーにのみ Node.js 18 以上が必要です。Windows、macOS、Linux で動作します。npm の新しいバージョンは、`--force` を付けてインストーラーを再実行するまで反映されません。

## クイックスタート

### Step 2: データを引く

```bash
python tools/mo.py check div text accordion-content
```

```
type               outcome     why
-----------------  ----------  -----------------------------------------------
accordion-content  BROKE_PAGE  AccordionItemElementMResource instance required
```

終了コードは 1 です。この type を単独で置くとコミットは成功しますが、公開ページ全体がエラー文字列になります。置くべき場所は `python tools/mo.py type accordion-content` が示します。

### Step 3: アシスタントに頼む

- 「Mosaic サイトにランディングセクションを作って：H1、段落、/contact/ へのボタン。」
- 「Mosaic の accordion-content は div の中に直接置ける？」
- 「各ステップを閉じると次へ進む、3 ステップのポップオーバーツアーを追加して。」

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

| ツール | 役割 | 触れる場所 |
|---|---|---|
| `mo.py` | 計測データの検索。入口 | ローカルの `data/` のみ |
| `build_page.py` / `build_site.py` | ガード付きの書き込み手順で仕様をコミット | あなたのサイト（REST） |
| `from_elementor.py` / `verify_conversion.py` | Elementor から Mosaic へ変換し、内容が届いたことを確認 | ローカルファイル／あなたのサイト |
| `verify_rwd.py`、`verify_browser.py`、`verify_*.py` | 配信ページを Chromium で読む | あなたのサイト（読み取り） |
| `theme_zip.py`、`theme_export.php` / `theme_import.php` | テーマ全体の移行 | あなたのサイト（REST／WP-CLI） |
| `data_upgrade.py` | プラグイン更新後に Mosaic のデータ移行を実行 | あなたのサイト（REST） |
| `scan_inline_tags.py` / `fix_inline_tags.py` | 1.0.11+ で HTML タグがそのまま表示されるテキストを検出・修正 | あなたのサイト（REST） |
| `test_mosaic.py`、`check_numbers.py` | セルフテストと数値チェック | このリポジトリ |

## 検証方法

node type、node プロパティ、スタイルプロパティ、スタイル状態はプラグインのソースから抽出し（`tools/check_tables.py` が再抽出して差分を確認）、実サイトに 1 つずつ書き込んで、配信された HTML とコンパイル後の CSS で確認しています。下の表はすべて `data/` にあり、行数は `tools/check_numbers.py` が照合します。

| テーブル | 行数 | 確認内容 |
|---|---:|---|
| `data/node-verification.csv` | 134 | すべての node type を単独でコミットし、公開ページから読み戻す |
| `data/style-verification.csv` | 101 | すべてのスタイルプロパティをコンパイル後の CSS と照合 |
| `data/node-property-verification.csv` | 191 | 各 node プロパティを、そのバリデーターが受け付ける値で検査 |
| `data/style-state-verification.csv` | 59 | 各状態を、それが生成するはずのセレクターと照合 |
| `data/rwd-verification.csv` | 733 | すべての `_t` / `_m` 宣言を実際に配信されたスタイルシートと照合 |
| `data/browser-verification/` | 4,132 | 3 つの画面幅での Chromium の計算後スタイル |
| `data/popover-verification.csv` | 37 | ポップオーバー：配置、閉じ方、反転、連鎖するツアー |
| `data/menu-verification.csv` | 34 | ホバーのドロップダウンとスマホ用メニューをマウス・キーボード・タッチで操作 |
| `data/form-surface-verification.csv` | 23 | すべてのフォーム項目（組み立て式の Select を含む） |
| `data/custom-fields-verification.csv` | 62 | ACF と Meta Box のフィールドを `@VAR` / `@LOOP` で読み出す |
| `data/theme-zip-verification.csv` | 22 | Mosaic 自身のテーマ ZIP を往復させて比較 |
| `data/conversion-batch.csv` | 19 | あるサイトのすべての Elementor ページを変換・構築・検査 |

- セルフテスト：`python tools/test_mosaic.py`、オフラインの 43 項目（検索、中国語の用語、構築結果の形と拒否ルール、公開されている構築インターフェース、このリポジトリの数値とプライバシー）。
- evals：Mosaic 1.0.10〜1.0.12 の挙動に関する 16 問。skill ありで 16/16、なしで 0/16。結果：[evals/RESULTS.md](evals/RESULTS.md)。
- `SKILL.md`、これらの README、バッジの数値は、`tools/check_numbers.py` がデータと照合しています。詳細：[verification-record.md](references/verification-record.md)。

1 回の検索にかかるトークン：同じ 6 つのタスクを tiktoken で計測（`data/token-benchmark.csv`、テーブル作成時に計測。`tools/benchmark_tokens.py` で再現できます）。テーブルを丸ごと読み込まず、検索してください。

| `mo.py` コマンド | ソースを読む | 全テーブルを読む | 検索 |
|---|---:|---:|---:|
| `params text ; params button ; prop url` | 10,005 | 259,539 | **961** |
| `style --grouped ; css border-left-width ; css border-radius` | 3,490 | 259,539 | **396** |
| `type accordion-content ; placement accordion-item` | 15,615 | 259,539 | **397** |
| `states --verified` | 3,619 | 259,539 | **1,054** |
| `css grid-column` | 1,862 | 259,539 | **51** |
| `stats ; check div text button accordion-content` | 63,172 | 259,539 | **288** |

## 制限

- Mosaic Pro 1.0.13 まで計測済みです。1.0.13 のエディターにしかない機能（新しいスタイル変数の種類、List のクラス、pageLoad の遅延など）はまだ計測しておらず、ツールも書き込みません。
- グリッド子要素の配置プロパティは headless で書き込んでも出力されません。一部のインタラクションの形はまだ計測していません。
- ブラウザー検証ツールには Playwright と書き込み可能なサイトが必要で、オフラインのセルフテストには含まれません。
- 未解決の項目：[data/pending.csv](data/pending.csv)。詳しいガイド（失敗モード、Elementor 変換、作例）：[docs/guide.md](docs/guide.md)（英語）。

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
