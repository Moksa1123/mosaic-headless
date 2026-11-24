<h1 align="center">Mosaic Headless</h1>

<h3 align="center">Mosaic Pro 無編輯器建站工具</h3>

<p align="center">
  <strong>實測資料模型 · 有防護的建頁工具 · 驗證實際送出的頁面</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3-blue?style=flat-square&logo=python&logoColor=white" alt="Python 3">
  <img src="https://img.shields.io/badge/node-18_or_later-green?style=flat-square&logo=node.js&logoColor=white" alt="Node.js 18 以上">
  <img src="https://img.shields.io/badge/playwright-browser_verifiers-blueviolet?style=flat-square" alt="瀏覽器驗證器用 Playwright">
  <img src="https://img.shields.io/badge/WP--CLI-server_scripts-blue?style=flat-square&logo=wordpress&logoColor=white" alt="伺服器腳本用 WP-CLI">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/node_types-134-success?style=flat-square" alt="134 種 node type">
  <img src="https://img.shields.io/badge/node_properties-120-success?style=flat-square" alt="120 個 node 屬性">
  <img src="https://img.shields.io/badge/style_properties-101-success?style=flat-square" alt="101 個樣式屬性">
  <img src="https://img.shields.io/badge/responsive_checks-733-blueviolet?style=flat-square" alt="733 條 RWD 檢查">
  <img src="https://img.shields.io/badge/self--tests-55-blueviolet?style=flat-square" alt="55 項自我測試">
</p>

<p align="center">
  <a href="https://www.npmjs.com/package/mosaic-headless"><img src="https://img.shields.io/npm/v/mosaic-headless?style=flat-square&logo=npm" alt="npm 版本"></a>
  <a href="https://www.npmjs.com/package/mosaic-headless"><img src="https://img.shields.io/npm/dt/mosaic-headless?style=flat-square&label=downloads&color=cb3837" alt="npm 下載數"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/Moksa1123/mosaic-headless?style=flat-square" alt="License"></a>
</p>

<p align="center"><a href="README.md">English</a> · <strong>正體中文</strong> · <a href="README.ja.md">日本語</a> · <a href="README.ko.md">한국어</a></p>

> 這是非官方的社群專案，不是 Mosaic Pro 的開發商 Nextend 製作或背書，也和 Nextend 沒有關係。Mosaic Pro 是需授權的第三方軟體，本專案不包含它。

## 功能

Mosaic 把頁面存在自己的資料表裡，一個元素一列，不在 `post_content`。這個 skill 是那套資料模型的實測地圖，加上透過它寫入的工具；資料從 Mosaic Pro 1.0.14 抽出，並在正式網站上逐一實測。

| 類別 | 內容 |
|---|---|
| 查詢 | `tools/mo.py`：134 種 node type、120 個 node 屬性、101 個樣式屬性、60 個樣式狀態，每項都附實測結論；中文和口語也查得到（`mo.py css 內距`） |
| 建頁 | `build_page.py`／`build_site.py` 透過 Mosaic 的 REST 寫入流程提交頁面規格，實測會弄壞頁面的寫法直接拒絕 |
| 驗證 | 用 Chromium 讀實際送出的頁面：RWD 規則、計算後樣式、選單、彈出視窗、輪播、表單 |
| 搬移 | 整個佈景匯出匯入；在 wp-admin 之外執行 Mosaic 的資料升級 |
| 轉換 | Elementor 頁面轉成 Mosaic 規格，轉不了的元素逐一列名 |

### 先查再寫

```bash
python tools/mo.py type accordion-content   # one type, joined to every live sweep
python tools/mo.py css 內距                  # Chinese works: padding-top/right/bottom/left
python tools/mo.py facts section padding     # measured front-end behaviour
```

### 透過防護建頁

```bash
python tools/mo.py skeleton > page.json
python tools/build_page.py --spec page.json   # refuses unsafe types, bad placement, out-of-enum values
```

### 檢查訪客實際拿到的頁面

```bash
python tools/verify_rwd.py --site page.json       # every _t/_m declaration in the served stylesheet
python tools/verify_browser.py --site page.json   # what Chromium computes, plus a design audit
```

## 適用情境

網站用的是 Mosaic Pro，想不開編輯器就建立或修改頁面、範本、元件、設計變數、彈出視窗、選單或互動，或想確切知道某個 Mosaic 設定的效果時使用。

| 需求 | 交給 |
|---|---|
| Elementor 頁面 | `elementor-headless` |
| 區塊編輯器（Gutenberg）頁面 | `gutenberg-headless` |
| SEO 文章、Rank Math 分數 | `rankmath-seo-wp` |
| 網站健康檢查、外掛更新、資安 | 不在範圍內 |

## 安裝

### Step 1: 選一種安裝方式

Claude plugin（Claude Code；上架 Claude 官方目錄後也可以從目錄安裝）：

```
/plugin install mosaic-headless --marketplace Moksa1123/mosaic-headless
```

npx，適用 Claude Code 和其他 AI 開發工具：

```bash
npx mosaic-headless@latest claude-code --global --force
npx mosaic-headless --list
```

手動複製：

```bash
git clone https://github.com/Moksa1123/mosaic-headless.git
cp -r mosaic-headless ~/.claude/skills/mosaic-headless
```

| 平台 | 安裝內容 | 位置 |
|---|---|---|
| Claude Code | 完整 skill：SKILL.md、references、tools、data、sites、evals、scripts | `~/.claude/skills/` 或 `./.claude/skills/` |
| Codex CLI | 完整 skill | `~/.codex/skills/` |
| Gemini CLI | 完整 skill | `~/.gemini/skills/` |
| GitHub Copilot | 完整 skill | `./.github/skills/` |
| Cursor | 一個內嵌 references 的 `.mdc` 規則檔 | `~/.cursor/rules/` |
| Windsurf | 一個內嵌 references 的規則檔 | `./.devin/rules/` |
| Continue | 一個內嵌 references 的規則檔 | `~/.continue/rules/` |
| Claude.ai | 上傳用 zip（SKILL.md、references、data、sites；不含工具） | 你存放的位置 |

系統需求：Python 3（查詢、建頁、自我測試只用標準函式庫）；瀏覽器驗證器需要 Playwright（見 `requirements.txt`）；`.php` 工具要在伺服器上有 WP-CLI；只有 npx 安裝程式需要 Node.js 18 以上。Windows、macOS、Linux 都能用。npm 出新版後，要用 `--force` 重跑安裝程式才會更新。

## 快速開始

### Step 2: 查資料

```bash
python tools/mo.py check div text accordion-content
```

```
type               outcome     why
-----------------  ----------  -----------------------------------------------
accordion-content  BROKE_PAGE  AccordionItemElementMResource instance required
```

它會以 exit code 1 結束：這個 type 單獨放進去，提交會成功，但整個公開頁面會變成一行錯誤字串。`python tools/mo.py type accordion-content` 會告訴你它該放在哪裡。

### Step 3: 跟 Claude 說

- 「在我的 Mosaic 網站做一個首屏區塊：一個 H1、一段文字、一個連到 /contact/ 的按鈕。」
- 「Mosaic 的 accordion-content 可以直接放在 div 裡嗎？」
- 「加一個三步驟的浮動框導覽，每一步關閉時進到下一步。」

## 觸發詞

English: Mosaic Pro, Nextend, build a Mosaic page without the editor, Mosaic padding / hover / breakpoint, Mosaic popup, popover, modal, Mosaic interaction, move a Mosaic theme, Mosaic upgrade, Elementor to Mosaic.

中文：Mosaic、Nextend、不開編輯器做頁面、內距、外距、圓角、懸停、斷點、RWD、彈出視窗、浮動框、摺疊面板、頁籤、輪播、互動、動畫、搬佈景、Mosaic 升級、Elementor 轉 Mosaic。

## 會執行與連線的內容

- **不會自己執行任何東西。** 沒有 hook、沒有 MCP server、沒有背景程序。只有 Claude 依照 `SKILL.md` 提出指令、你同意之後才會執行。
- **只在本機、不連網**：`tools/mo.py` 讀 `data/` 裡的 CSV 並印出答案；`tools/test_mosaic.py`、`tools/check_numbers.py` 讀這個 repo。都不寫入、不連線。
- **透過 REST API 連你的 WordPress 網站**：`build_page.py`、`build_site.py`、`data_upgrade.py`、`theme_zip.py`，以及 `sweep_*.py`、`probe*.py`，會呼叫你設定的那一個網站的 Mosaic REST 路由，讀寫頁面、元件、範本和佈景。只連那個網站。
- **透過 WP-CLI 在你的網站上執行**：`tools/*.php` 用 `wp eval-file` 在伺服器上（通常是你自己的 SSH）跑在你的 WordPress 裡，讀寫該網站的 Mosaic 資料表和佈景資料。`prune_unbound.php` 會刪資料，沒加 `apply` 這個字（不是 `--apply`）時只做試跑；`theme_delete.php` 會刪掉你指定的佈景，但不會刪使用中的佈景。
- **讀你的公開頁面**：`tools/verify_*.py`、`audit_mobile.py` 用 Playwright（Chromium）或 `urllib` 開同一個網站的頁面，比對送出的結果和寫入的內容。
- **帳密**：網站網址、WordPress 登入 cookie 和對應的 `wp_rest` nonce，必須是你自己網站的管理員。`tools/mint_session.php` 在伺服器上印出這三個值。以 plugin 安裝時，Claude Code 會用 `userConfig` 詢問；cookie 和 nonce 標為敏感資料，存在系統的憑證儲存區。也可以用環境變數（`MOSAIC_SITE_URL`、`MOSAIC_REST_COOKIE`、`MOSAIC_REST_NONCE`），或用 `--config` 傳入你自己的 JSON 檔。**任何工具都不會在你的電腦上找帳密。**
- **第三方**：`sites/` 裡的示範範例會載入 Google Fonts，所以用它建出來的頁面，訪客的瀏覽器會向 Google 取字型。
- 安裝時不下載任何東西，也不會把資料傳給作者或任何人。

| 工具 | 做什麼 | 碰到哪裡 |
|---|---|---|
| `mo.py` | 查詢實測資料，唯一入口 | 只讀本機 `data/` |
| `build_page.py` / `build_site.py` | 透過有防護的寫入流程提交規格 | 你的網站（REST） |
| `from_elementor.py` / `verify_conversion.py` | Elementor 轉 Mosaic，並證明內容都搬過來 | 本機檔案／你的網站 |
| `verify_rwd.py`、`verify_browser.py`、`verify_*.py` | 用 Chromium 讀實際送出的頁面 | 你的網站（唯讀） |
| `theme_zip.py`、`theme_export.php` / `theme_import.php` | 搬整個佈景 | 你的網站（REST／WP-CLI） |
| `sync_nodes.py` + `list_bindings.php` | 就地更新已建好的網站：只改有變的節點，沿用原本的 master；沒加 `--apply` 只預覽 | 你的網站（REST；綁定關係用 WP-CLI 讀） |
| `data_upgrade.py` | 外掛更新後執行 Mosaic 的資料遷移 | 你的網站（REST） |
| `scan_inline_tags.py` / `fix_inline_tags.py` | 找出並修正 1.0.11+ 會把 HTML 標籤印出來的文字 | 你的網站（REST） |
| `test_mosaic.py`、`check_numbers.py` | 自我測試、數字核對 | 這個 repo |

## 驗證方式

node type、node 屬性、樣式屬性、樣式狀態從外掛原始碼抽出（`tools/check_tables.py` 會重新抽取並比對），再逐一寫進正式網站，檢查實際送出的 HTML 和編譯後的 CSS。下表每張資料表都在 `data/`，列數由 `tools/check_numbers.py` 核對。

| 資料表 | 列數 | 檢查了什麼 |
|---|---:|---|
| `data/node-verification.csv` | 134 | 每種 node type 單獨提交，再從公開頁面讀回 |
| `data/style-verification.csv` | 101 | 每個樣式屬性對照編譯後的 CSS |
| `data/node-property-verification.csv` | 191 | 每個 node 屬性用它自己的驗證器接受的值測試 |
| `data/style-state-verification.csv` | 59 | 每個狀態對照它應該產生的選擇器 |
| `data/rwd-verification.csv` | 733 | 每條 `_t` / `_m` 宣告對照網站實際送出的樣式表 |
| `data/browser-verification/` | 4,132 | Chromium 在三種寬度下的計算後樣式 |
| `data/popover-verification.csv` | 37 | 浮動框：定位、關閉、翻轉、串連導覽 |
| `data/menu-verification.csv` | 34 | 懸停下拉選單和手機選單，用滑鼠、鍵盤、觸控操作 |
| `data/form-surface-verification.csv` | 23 | 每種表單欄位，包括可組裝的 Select |
| `data/custom-fields-verification.csv` | 62 | ACF 和 Meta Box 欄位透過 `@VAR` / `@LOOP` 讀出 |
| `data/theme-zip-verification.csv` | 22 | Mosaic 自己的佈景 ZIP 匯出再匯入並比對 |
| `data/conversion-batch.csv` | 19 | 一個網站的每個 Elementor 頁面都轉換、建置並檢查 |

- 自我測試：`python tools/test_mosaic.py`，55 項離線測試（查詢、中文用語、建頁產出的結構與拒收規則、對外的建頁介面、本 repo 的數字與隱私）。
- evals：16 題 Mosaic 1.0.10 到 1.0.12 的行為題；有 skill 16/16，沒有 skill 0/16。結果見 [evals/RESULTS.md](evals/RESULTS.md)。
- `SKILL.md`、這幾份 README 和徽章上的數字，都由 `tools/check_numbers.py` 對照資料核對。細節見 [verification-record.md](references/verification-record.md)。

查一次要花多少 token：同樣 6 項任務用 tiktoken 計算（`data/token-benchmark.csv`，建表當時量的；`tools/benchmark_tokens.py` 可重現）。不要把資料表整個讀進來，用查的。

| `mo.py` 指令 | 讀原始碼 | 讀全部資料表 | 查詢 |
|---|---:|---:|---:|
| `params text ; params button ; prop url` | 10,005 | 259,539 | **961** |
| `style --grouped ; css border-left-width ; css border-radius` | 3,490 | 259,539 | **396** |
| `type accordion-content ; placement accordion-item` | 15,615 | 259,539 | **397** |
| `states --verified` | 3,619 | 259,539 | **1,054** |
| `css grid-column` | 1,862 | 259,539 | **51** |
| `stats ; check div text button accordion-content` | 63,172 | 259,539 | **288** |

## 限制

- 實測到 Mosaic Pro 1.0.14。只存在於 1.0.13 編輯器裡的功能（新的樣式變數類型、List 的 class、pageLoad 延遲等）還沒實測，工具也不會寫。
- 用 headless 方式寫入格線子項位置的屬性不會有輸出；部分互動形狀還沒實測。
- 瀏覽器驗證器需要 Playwright 和一個可以寫入的網站，不在離線自我測試裡。
- 待補問題：[data/pending.csv](data/pending.csv)。完整說明（失敗模式、Elementor 轉換器、示範範例）：[docs/guide.md](docs/guide.md)（英文）。

## 目錄結構

```
SKILL.md          Claude 載入的內容：資料出處、路由、任務、驗證
data/             實測資料表（CSV）、中文用語、待補清單
references/       主題說明：資料模型、樣式、彈出視窗、升級⋯
tools/            mo.py、建頁與驗證工具、WP-CLI 腳本、自我測試
sites/            示範範例（可讀的 Python 模組）
evals/            評分題目與結果
scripts/          安裝程式與發版檢查
assets/           各平台的安裝範本
docs/             完整說明
.claude-plugin/   plugin 與 marketplace 設定
```

## 授權與作者

MIT License。作者 Moksa（[moksaweb.com](https://moksaweb.com)）。問題回報：[GitHub](https://github.com/Moksa1123/mosaic-headless/issues)。
