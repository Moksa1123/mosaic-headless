# mosaic-headless

直接寫入資料模型來建置和修改 Mosaic Pro（Nextend）WordPress 網站：不開視覺編輯器、不操作 DOM，每個查詢都用正式網站上的實測結果回答。

[![npm](https://img.shields.io/npm/v/mosaic-headless?style=flat-square)](https://www.npmjs.com/package/mosaic-headless)
[![License: MIT](https://img.shields.io/github/license/Moksa1123/mosaic-headless?style=flat-square)](LICENSE)

[English](README.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

> 這是非官方的社群專案，不是 Mosaic Pro 的開發商 Nextend 製作或背書，也和 Nextend 沒有關係。Mosaic Pro 是需授權的第三方軟體，本專案不包含它。

## 功能

Mosaic 把頁面存在自己的資料表裡，一個元素一列，不在 `post_content`。這個 skill 是那套資料模型的實測地圖，加上透過它寫入的工具。

- **查了再寫，不用猜**：`tools/mo.py` 回答 node type、屬性、樣式鍵、狀態叫什麼、值要寫成什麼形狀、能放在哪裡、安不安全。資料涵蓋 134 種 node type、120 個 node 屬性、101 個樣式屬性、60 個樣式狀態，從 Mosaic Pro 1.0.13 抽出，並在正式網站上逐一實測。
- **中文和口語也查得到**：`mo.py css 內距` 會找到 padding；用語以 Mosaic 自己的正體中文介面為準。
- **建頁面和整站**：`build_page.py`、`build_site.py` 透過 Mosaic 的 REST 寫入流程提交頁面規格，實測會弄壞頁面的寫法直接拒絕。
- **檢查實際送出的頁面**：驗證器用 Chromium 讀公開頁面（RWD 規則、計算後樣式、選單、彈出視窗、輪播、表單），不只相信提交成功。
- **搬移與轉換**：匯出匯入整個佈景、執行 Mosaic 的資料升級、把 Elementor 頁面轉成 Mosaic。

## 適用情境

網站用的是 Mosaic Pro，想不開編輯器就建立或修改頁面、範本、元件、設計變數、彈出視窗、選單或互動，或想確切知道某個 Mosaic 設定的效果時使用。

其他頁面建構器不適用：Elementor 頁面交給 `elementor-headless`，區塊編輯器頁面交給 `gutenberg-headless`，SEO 文章交給 `rankmath-seo-wp`。不處理 WordPress 網站健康檢查、外掛更新或資安。

## 安裝

Claude plugin（Claude Code；上架 Claude 官方目錄後也可以從目錄安裝）：

```
/plugin install mosaic-headless --marketplace Moksa1123/mosaic-headless
```

npx，適用 Claude Code 和其他 AI 開發工具（Cursor、Codex CLI、Gemini CLI、Copilot、Continue、Windsurf、Claude.ai 上傳用的 zip）：

```bash
npx mosaic-headless@latest claude-code --global --force
npx mosaic-headless --list
```

手動複製：

```bash
git clone https://github.com/Moksa1123/mosaic-headless.git
cp -r mosaic-headless ~/.claude/skills/mosaic-headless
```

系統需求：Python 3（查詢、建頁、自我測試只用標準函式庫）；瀏覽器驗證器需要 Playwright（見 `requirements.txt`）；`.php` 工具要在伺服器上有 WP-CLI；Node.js 只有 npx 安裝程式需要。Windows、macOS、Linux 都能用。npm 出新版後，要用 `--force` 重跑安裝程式才會更新。

## 快速開始

可以這樣跟 Claude 說：

- 「在我的 Mosaic 網站做一個首屏區塊：一個 H1、一段文字、一個連到 /contact/ 的按鈕。」
- 「Mosaic 的 accordion-content 可以直接放在 div 裡嗎？」
- 「加一個三步驟的浮動框導覽，每一步關閉時進到下一步。」

或自己查資料：

```bash
python tools/mo.py check div text accordion-content
```

```
type               outcome     why
-----------------  ----------  -----------------------------------------------
accordion-content  BROKE_PAGE  AccordionItemElementMResource instance required
```

它會以 exit code 1 結束：這個 type 單獨放進去，提交會成功，但整個公開頁面會變成一行錯誤字串。`python tools/mo.py type accordion-content` 會告訴你它該放在哪裡。

## 觸發詞

English: Mosaic Pro, Nextend, build a Mosaic page without the editor, Mosaic padding / hover / breakpoint, Mosaic popup, popover, modal, Mosaic interaction, move a Mosaic theme, Mosaic upgrade, Elementor to Mosaic.

中文：Mosaic、Nextend、不開編輯器做頁面、內距、外距、圓角、懸停、斷點、RWD、彈出視窗、浮動框、摺疊面板、頁籤、輪播、互動、動畫、搬佈景、Mosaic 升級、Elementor 轉 Mosaic。

## 會執行與連線的內容

- **不會自己執行任何東西。** 沒有 hook、沒有 MCP server、沒有背景程序。只有 Claude 依照 `SKILL.md` 提出指令、你同意之後才會執行。
- **只在本機、不連網**：`tools/mo.py` 讀 `data/` 裡的 CSV 並印出答案；`tools/test_mosaic.py`、`tools/check_numbers.py` 讀這個 repo。都不寫入、不連線。
- **透過 REST API 連你的 WordPress 網站**：`build_page.py`、`build_site.py`、`data_upgrade.py`、`theme_zip.py`，以及 `sweep_*.py`、`probe*.py`，會呼叫你設定的那一個網站的 Mosaic REST 路由，讀寫頁面、元件、範本和佈景。只連那個網站。
- **透過 WP-CLI 在你的網站上執行**：`tools/*.php` 用 `wp eval-file` 在伺服器上（通常是你自己的 SSH）跑在你的 WordPress 裡，讀寫該網站的 Mosaic 資料表和佈景資料。`theme_delete.php`、`prune_unbound.php` 會刪資料，沒加 `--apply` 時只做試跑。
- **讀你的公開頁面**：`tools/verify_*.py`、`audit_mobile.py` 用 Playwright（Chromium）或 `urllib` 開同一個網站的頁面，比對送出的結果和寫入的內容。
- **帳密**：網站網址、WordPress 登入 cookie 和對應的 `wp_rest` nonce，必須是你自己網站的管理員。`tools/mint_session.php` 在伺服器上印出這三個值。以 plugin 安裝時，Claude Code 會用 `userConfig` 詢問；cookie 和 nonce 標為敏感資料，存在系統的憑證儲存區。也可以用環境變數（`MOSAIC_SITE_URL`、`MOSAIC_REST_COOKIE`、`MOSAIC_REST_NONCE`），或用 `--config` 傳入你自己的 JSON 檔。**任何工具都不會在你的電腦上找帳密。**
- **第三方**：`sites/` 裡的示範範例會載入 Google Fonts，所以用它建出來的頁面，訪客的瀏覽器會向 Google 取字型。
- 安裝時不下載任何東西，也不會把資料傳給作者或任何人。

## 驗證方式

- node type、node 屬性、樣式屬性、樣式狀態從外掛原始碼抽出（`tools/check_tables.py` 會重新抽取並比對），再逐一寫進正式網站，檢查實際送出的 HTML 和編譯後的 CSS。
- 示範頁面用 Chromium 重讀：733 條 RWD 宣告對照網站實際送出的樣式表，4,132 筆三種寬度的計算後樣式。細節見 [verification-record.md](references/verification-record.md)。
- 自我測試：`python tools/test_mosaic.py`，42 項離線測試（查詢、中文用語、建頁產出的結構與拒收規則、對外的建頁介面、本 repo 的數字與隱私）。
- evals：16 題 Mosaic 1.0.10 到 1.0.12 的行為題；有 skill 16/16，沒有 skill 0/16。結果見 [evals/RESULTS.md](evals/RESULTS.md)。
- `SKILL.md` 和這幾份 README 裡的數字，都由 `tools/check_numbers.py` 對照資料核對。

## 限制

- 實測到 Mosaic Pro 1.0.13。只存在於 1.0.13 編輯器裡的功能（新的樣式變數類型、List 的 class、pageLoad 延遲等）還沒實測，工具也不會寫。
- 用 headless 方式寫入格線子項位置的屬性不會有輸出；部分互動形狀還沒實測。
- 瀏覽器驗證器需要 Playwright 和一個可以寫入的網站，不在離線自我測試裡。
- 待補問題：[data/pending.csv](data/pending.csv)。完整說明（失敗模式、token 成本、Elementor 轉換器、示範範例）：[docs/guide.md](docs/guide.md)（英文）。

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
