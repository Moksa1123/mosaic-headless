# mosaic-headless

[![npm downloads](https://img.shields.io/npm/dt/mosaic-headless?label=npm%20downloads&color=cb3837)](https://www.npmjs.com/package/mosaic-headless)

直接寫入資料模型來建置與修改 [Mosaic Pro](https://mosaicbuilder.com)（Nextend）網站——
不開視覺編輯器，不碰 DOM。把 Elementor 頁面轉進來。把整個主題搬到另一個站。
每一項宣稱都在真實站台上量過。

*其他語言：[English](README.md) · [日本語](README.ja.md) · [한국어](README.ko.md)*

---

## 安裝

```bash
npx mosaic-headless                          # 互動式：選平台
npx mosaic-headless claude-code --global     # Claude Code，裝到 ~/.claude/skills/
npx mosaic-headless cursor --to ./my-project
npx mosaic-headless --list                   # 全部八個平台
```

**更新不會自己發生。** npm 上有新版，不代表你的 agent 載入的那個資料夾有變；要重跑安裝器並加
`--force`（不加的話它會拒絕覆蓋你可能改過的 SKILL.md）：

```bash
npx mosaic-headless@latest claude-code --global --force
```

Python 3 和 Playwright 是*跑工具*時才需要，安裝不用。

## 這是什麼

Mosaic 把一個頁面放在 **23 張自訂資料表**裡，不在 `post_content`，也不在 `postmeta`。
一個元素一列，樹狀結構靠 `parentID` 欄位，同層順序是一個 fractional-index 字串。
編輯器只是這個模型的其中一個客戶端。它不是格式本身，而且你不需要它。

這個技能就是那個模型的地圖——對照真實站台量出來的，不是讀原始碼讀出來的——外加一組
工具：透過模型寫入、檢查寫出來的東西、把 Elementor 的頁面搬進來。

## 唯一的規則

**絕對不要憑記憶寫任何節點型別、屬性名稱、列舉值、樣式鍵或 Free/Pro 的判斷。去 `data/` 查。**

而且要用 `mo.py` 查，不要用 grep。grep 回答你打出來的問題，不回答你真正的問題。問它
`accordion-content`，它確認這個型別存在；掃描表則說 BROKE_PAGE——放一個下去，整個公開頁面
會變成一段 54 bytes 的錯誤字串。兩個都是真的，也都是錯的答案：列旁邊的註記說那段字串
指名的是「缺少父層」，而照 `accordion > accordion-item` 嵌套後它能寫入、能渲染，還免費送你
一個鍵盤可操作的展開元件。`mo.py type` 一次把三者都給你。

```bash
python tools/mo.py type accordion-content   # 一個型別，接上所有線上掃描結果
python tools/mo.py check div text button    # 遇到不安全或不存在的型別就以 1 退出
python tools/mo.py params text              # 一個型別上所有能設的東西
python tools/mo.py style --grouped          # 單獨設定就無效的那 20 個
python tools/mo.py states --verified        # 實測會編譯的狀態
python tools/mo.py css grid-column          # 哪個 Mosaic 鍵驅動這條 CSS
```

然後去看頁面。Mosaic 有**七種**失敗模式，只有兩種會改變 HTTP 狀態碼：

```
驗證器乾淨拒絕            HTTP 200 + 內文帶 `exceptions` 陣列
commit 時 PHP fatal       HTTP 500（122 個型別裡有 15 個放在一般 div 下會這樣）
結構無效的節點            HTTP 200、已寫入、資料庫有那一列，然後整個公開頁面
                          變成 54 bytes 的錯誤字串
值的「形狀」錯了          HTTP 200、存進去了，CSS 規則就是不出現
規則對、結果錯            HTTP 200、樣式表裡有、寫得對，瀏覽器算出另一個值
該網址沒有模板            HTTP 406，未登入者拿到空白內文
內容造成渲染時 fatal      HTTP 500——commit 通過了，Mosaic 解析頁面時死掉。`code` 節點
                          的內容是模板：壓縮 CSS 慣用的 `@media(` 會被讀成函式呼叫。
                          `@media (` 就正常。build_page 會拒絕前者。
```

commit 成功不代表頁面能用，樣式表正確也不代表。這裡每個工具都會在寫入後把頁面抓回來——
而且把 5xx 當成空頁面，因為 WordPress 的「嚴重錯誤」畫面有 2,697 bytes，比任何天真的
「健康頁面」門檻都大。

## 驗證了什麼，怎麼驗的

全部在真實站台上跑——WordPress 7.1、WooCommerce 11.1、Mosaic Pro 1.0.7，**未授權**：
授權鎖的是主題庫和更新，不是節點工廠，所以 Pro 型別照樣註冊、照樣渲染。

| 項目 | 結果 |
|---|---|
| **節點型別** | 122 / 122 逐一放進獨立文件，寫入 → 渲染 → 斷言 → 刪除：70 RENDERED、30 COMMITTED、15 COMMIT_5xx、7 BROKE_PAGE。未渲染的當中有三個是「沒給父層」的掃描方法產物，註記就在列旁 |
| **樣式屬性** | 98 / 98 寫進真實頁面、對照編譯出的 CSS：58 COMPILED、18 ABSENT、21 SKIPPED |
| **節點屬性** | 181 / 181 用各自驗證鏈推出的值重新探測：35 APPLIED、42 NO_EFFECT、55 NO_HOST、47 SKIPPED |
| **響應式** | 兩個站共 731 條 `_t`/`_m` 宣告，對照網站實際送出的樣式表逐條斷言——全數通過 |
| **瀏覽器** | 在 Chromium 三個視窗寬度上對兩個交付頁面做 3,988 次計算樣式讀取：2,929 條比對相符、912 條標為無法比對、**0 條被覆蓋** |
| **設計稽核** | 對比度、字體回退、CJK 字距、水平溢出、文字裁切、每行字數——在瀏覽器裡跑，**26 項發現，每一項都有書面裁定**——沒寫理由的 acknowledge 會被發布閘門拒絕 |
| **元件** | 元件系統從頭驅動到尾，**8 之 8**：在分類下建立、文件自癒、透過可寫實例填入樹、唯讀實例拒絕同一筆寫入作為負控制、頁面上兩個實例渲染同一個定義 |
| **樣式狀態** | 53 個狀態中的 52 個寫進真實頁面，對照表格承諾的選擇器：**36 個完全吻合**、12 NO_HOST、3 SKIPPED、1 BROKE_PAGE。偽類是大寫輸出的（`.M_EL9:HOVER`） |
| **互動** | JS 動畫路徑以負控制探測並讀回資料列：`propertyMetas` **會**被接受並儲存；屬性值仍然綁不上，但邊界現在是精確的 |
| **accordion** | `accordion-item` 與 `accordion-content` 在掃描表裡是 BROKE_PAGE；照工廠要求嵌套後能寫入、能渲染，**7 之 7** |
| **入口動畫** | 以單調時鐘在十五個時間點取樣、做八項斷言。相較於完全沒有動畫的同一頁只多掉一幀，因為它會等文件第一次排版做完才開始 |
| **永續動畫** | 右下角一塊不斷自我印刷、點了會放大的版子，**28 項檢查**：暫停時間軸逐格比對證明週期性、五個寬度、二十五個捲動停點量文字*與*控制項的遮擋、以「永遠讀不到」為失敗條件、指標和 Enter 都能打開、reduced motion 下靜止 |
| **Elementor 轉換** | 一個正式站的全部 Elementor 頁面——19 頁、3,292 個元素——轉換、建置、對照來源檢查：**19 之 19**，3,281 個元素搬過去、11 個書面宣告。再把轉出的頁面跑過響應式、瀏覽器和稽核，每一項發現都分類為「繼承」或「引入」：**引入 0 個** |
| **主題匯出／匯入** | 兩條路徑，都來回驗證過。`theme_export.php` 用 WP-CLI 把資料列搬成 JSON、ID 不變。`theme_zip.py` 驅動 Mosaic **自己**的 ZIP 匯出匯入——匯入預設進 test mode，要 `--activate` 才上線，因為它的預設是直接切換 live 站——**22 項檢查**逐表、逐樹比對副本與來源 |
| **技能本身** | `claude plugin eval .`——五個使用者真的會問的問題，各跑三次，有載技能和沒載各一臂，每次三個 LLM 裁判。**有：五題全 1.00。沒有：五題全 0.00。** 基準線最好的回答是拒答 |
| **線上量測** | 114 條 REST 路由、151 個 element class、59 個條件主體、23 張表 / 206 個欄位 |

`SKIPPED`、`NO_HOST`、`INCONCLUSIVE` 從不折算進通過率。把自己的盲點算成成功的掃描，
正是這個技能反對的東西。

### 動手前值得知道的結果

**屬於某個 `group` 的屬性單獨設定時無效。** 兩個方向都精確：78 個未分組屬性給出 58 COMPILED、
0 ABSENT；20 個分組屬性全部 0 COMPILED。所以 `borderLeftWidth`、`outlineColor`、`gridColumnStart`
是同一條規則的三個實例。用分組形狀——`border` 吃 `{width, style, color}`——或 `customStyles`。

**斷點覆寫可以「改」一個屬性，永遠不能「拿掉」一個。** 窄螢幕的 `customStyles` 只是不提邊框，
寬螢幕的邊框就繼續站在那裡。把 `border-left:0` 說出口。

**只有四個型別吃 `url`**：`button`、`menu-link`、`wysiwyg-link`、`dropdown-toggle`。放在 `text`
或 `image` 上會被接受、被存下、然後不產生任何錨點。改用 `menu-link` 包起來——它接受任意子節點，
一有 `url` 就變成真正的 `<a href>`。

**圖片的 attachment protocol 路徑是相對 uploads 目錄的。**
`wp-attachment://image/<id>/full/2026/09/pic.png` 能解析，還會帶出附件的寬高。給它完整的
`wp-content/uploads/...` 路徑——最直覺的猜法——Mosaic 會把 uploads 前綴再接一次，而且不報錯。

## Elementor → Mosaic

```bash
wp post meta get 2360 _elementor_data > page.json
python tools/from_elementor.py --data page.json --out spec.json --report conv.csv \
    --uploads-base https://site/wp-content/uploads --slug works --post 208
python tools/build_site.py --config c.json --site spec.json
python tools/verify_conversion.py --data page.json --url https://site/works/ --report conv.csv
```

範圍是數出來的，不是憑喜好定的：一個真實站的 19 頁裡，container / heading / text-editor /
button / html / icon-list / divider / image 佔了全部元素的 99.6%。長尾——loop grid、表單、倒數、
第三方 addon——是動態的，沒有節點可以變成；每一個都按名稱和原因列進報告、絕不默默丟掉，
`--strict` 則拒絕產出有損的 spec。

版面、字體、顏色、邊框、連結、圖片都會過去，三個斷點都帶（`_tablet`/`_mobile` → `_t`/`_m`）。
不會過去的：進場動畫（Mosaic 的互動綁定未解）、shape divider、漸層疊加。驗證器接著拿建好的
頁面對照來源——每個字串、圖片、連結、標題層級——它馬上就證明了自己的價值：抓到轉換器把
`url` 寫在不理它的節點上，漏了 21 個連結中的 19 個。

## 工具

| 工具 | 用途 |
|---|---|
| `mo.py` | 查詢量測過的表面——**正門** |
| `build_page.py` / `build_site.py` | 透過有守門的寫入路徑 commit 一份 spec；量到會壞的一律拒絕 |
| `from_elementor.py` / `verify_conversion.py` | Elementor → Mosaic，以及內容確實到達的證明 |
| `verify_browser.py` | 瀏覽器算出來的是不是樣式表承諾的，以及有沒有通過設計稽核 |
| `verify_rwd.py` | 每條 `_t`/`_m` 宣告有沒有進到送出的樣式表 |
| `verify_intro.py` / `verify_loop.py` | 會「結束」的載入動畫；會循環、不遮東西、能打開的永續動畫 |
| `theme_export.php` / `theme_import.php` | 整個主題以 JSON 資料列透過 WP-CLI 搬移，ID 不變 |
| `theme_zip.py` / `theme_zip_compare.php` / `theme_delete.php` | 在編輯器外驅動 Mosaic 自己的 ZIP 匯出匯入、副本對來源逐樹比對、以及拒絕刪 live 主題的乾淨刪除 |
| `sweep_*.py` / `probe_*.py` | 那些表格是用這些儀器量出來的 |
| `bootstrap_probe_theme.php` / `mint_session.php` | 免授權的實驗主題，以及從 WP-CLI 鑄出 REST session |

## 線上的工作範例

`sites/_moksa.py` 只透過資料表建出一個真實的工作室網站，隨套件出貨作為參考。它就在
**https://mosaic.moksaweb.com/**：1,286 個節點的首頁，用具名 view timeline 做捲動追蹤的條款索引；
一段一次印一塊版、把浮世繪印出來的入口動畫；一塊在角落永遠印下去、點了會放大的版子；
還有一個 WooCommerce [My Account](https://mosaic.moksaweb.com/my-account/) 頁，它的 UI 全部
透過一個跑 shortcode 的 `code` 節點進來。全程沒有自己寫任何 JavaScript。

## 從哪裡開始

1. `references/data-model.md`——頁面實際住在哪裡。
2. `references/write-protocol.md`——checkout / check / commit。
3. `references/failure-modes.md`——Mosaic 怎麼失敗，量測版。**動手前先讀。**
4. `references/responsive.md`——狀態／斷點／屬性三軸。
5. `references/styling.md`——樣式值怎麼變成 CSS。
6. `references/design-system.md`——element class 與設計 token。

## 發版

```bash
npm version minor      # 更新 package.json、SKILL.md 和八個平台模板的版號，
                       # commit、打 tag、push；tag 觸發 release.yml
```

`bin/check-release.mjs` 把關每一次發版，檢查的是容易出錯而不是容易檢查的事：版號一致、
`files` 的每個 glob 都對到東西、每張驗證表的列數仍然等於 SKILL.md 和四份 README 引用的數字、
沒有未裁定的設計稽核發現、eval 套件在場，以及**直接檢查 tarball 本身**——npm 的 `files` 白名單
會蓋過 `.gitignore`，曾經把一個真實客戶的網站放進即將發布的套件裡。

發布走 npm trusted publishing（OIDC）：哪裡都沒有 token。npmjs.com 套件設定的 Trusted Publisher：
GitHub Actions、`Moksa1123` / `mosaic-headless`、workflow `release.yml`、environment **留空**。

## 授權

MIT。Mosaic Pro 本身是授權的第三方軟體，**不**包含在此。
