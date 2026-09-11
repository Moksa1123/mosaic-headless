# mosaic-headless

[![npm downloads](https://img.shields.io/npm/dt/mosaic-headless?label=npm%20downloads&color=cb3837)](https://www.npmjs.com/package/mosaic-headless)

直接寫入資料模型來建置與修改 [Mosaic Pro](https://mosaicbuilder.com)（Nextend）網站——
不開視覺編輯器，不碰 DOM。

*其他語言：[English](README.md) · [日本語](README.ja.md) · [한국어](README.ko.md)*

---

Mosaic 把一個頁面放在 **23 張自訂資料表**裡，不在 `post_content`，也不在 `postmeta`。
一個元素一列，樹狀結構靠 `parentID` 欄位，同層順序是一個 fractional-index 字串。
編輯器只是這個模型的其中一個客戶端。它不是格式本身，而且你不需要它。

這個 skill 就是那個模型的地圖——**對著真實安裝量出來的，不是從原始碼讀出來的**。

## 唯一一條凌駕一切的規則

**絕不憑印象寫節點型別、屬性名稱、列舉值、樣式鍵或 Free/Pro 的判斷。到 `data/` 裡查。**

而且要用 `mo.py` 查，不要用 grep。grep 回答你打出來的問題，不回答你真正的問題：
問它 `accordion-content`，它確認這個型別存在；掃描表則說 BROKE_PAGE——放一個下去，
整個公開頁面會變成一段 54 bytes 的錯誤字串。兩個都是真的，也都是錯的答案：列旁邊的
註記說那段字串指名的是「缺少父層」，而照 `accordion > accordion-item` 嵌套後它能寫入、
能渲染，還免費送你一個鍵盤可操作的展開元件。`mo.py type` 一次把三者都給你。

```bash
python tools/mo.py type accordion-content   # 一個型別，接上所有線上掃描結果
python tools/mo.py check div text button    # 型別不安全或不存在就 exit 1
python tools/mo.py style --grouped          # 那 20 個單獨設定必然無效的屬性
python tools/mo.py states --verified        # 實測會編譯出來的狀態
python tools/mo.py params text              # 一個型別上所有能設的東西
```

然後去看頁面。Mosaic 有四種失效模式，**其中只有一種會改變 HTTP 狀態碼**：

```
驗證器乾淨地拒絕      HTTP 200  + body 裡一個 exceptions 陣列
commit 時 PHP fatal   HTTP 500  （122 種型別裡有 15 種，光放在 div 裡就會）
結構無效的節點        HTTP 200、已寫入、資料庫有那一列，然後整個公開頁面
                      變成一段 54 bytes 的錯誤字串
值的「形狀」錯誤      HTTP 200、已儲存，而那條 CSS 規則就是不存在
規則對，結果不對      HTTP 200、在樣式表裡、內容正確，而瀏覽器算出來是另一回事
該網址沒有對應範本    HTTP 406，而且對未登入者是空白 body
```

**commit 成功不能當作頁面正常的證據，樣式表正確也不能。**

## 驗證了什麼，怎麼驗的

全部跑在真實安裝上——WordPress 7.1、WooCommerce 11.1、Mosaic Pro 1.0.7、**未授權**：
授權管的是主題庫與更新，不是節點工廠，所以 Pro 型別照樣註冊、照樣渲染。

| 項目 | 結果 |
|---|---|
| **節點型別** | 122 / 122，一份文件一種型別：寫入 → 渲染 → 斷言 → 刪除。70 RENDERED、30 COMMITTED、15 COMMIT_5xx、7 BROKE_PAGE |
| **樣式屬性** | 98 / 98 寫進真實頁面並對照編譯後的 CSS：58 COMPILED、18 ABSENT、21 SKIPPED |
| **節點屬性** | 181 / 181，用每個屬性自己的 validator chain 推導出的值重測：35 APPLIED、42 NO_EFFECT、55 NO_HOST、47 SKIPPED |
| **響應式** | 兩個站共 731 條 `_t`/`_m` 宣告，對照網站實際送出的樣式表逐條斷言——全數通過 |
| **元件系統** | 完整驅動過一遍，**8 / 8**：在分類下建立、文件 heal、透過可寫的 instance 填入內容、唯讀的那個作為負對照組確實拒絕同一個寫入，最後兩個實例在頁面上由同一份定義渲染兩次 |
| **樣式狀態** | 53 個狀態中的 52 個寫進真實頁面，對照表格承諾的選擇器逐一比對：**36 個完全吻合**、12 個 NO_HOST、3 個 SKIPPED、1 個 BROKE_PAGE。七個可用於任何元素的狀態全數驗證 |
| **互動動畫** | 帶負對照組並讀回儲存列來探測 JS 動畫路徑：`propertyMetas` **確實**會被接受並儲存；屬性值仍然無法綁定，但界線現在很精確 |
| **入口動畫** | 以單調時鐘在載入後十五個時間點取樣、做八項斷言——它有播、被動畫的 `@property` 計數器跑到 100、遮罩退出點擊判定、視窗內沒有任何內容卡在 opacity 0、真實點擊落在文件上、`prefers-reduced-motion` 下遮罩根本不存在、而一切靜止後仍有東西在動。相較於完全沒有動畫的同一頁只多掉一幀，因為它會等文件第一次排版做完才開始 |
| **永續動畫** | 右下角一塊不斷自我印刷、點了會放大的版子，**28 項檢查**：暫停時間軸逐格比對證明週期性、在五個寬度、二十五個捲動停點量文字*與*控制項的遮擋、以「永遠讀不到」為失敗條件、用指標和 Enter 都能打開、reduced motion 下靜止。建在 Mosaic 自己的 accordion 上 |
| **accordion** | `accordion-item` 與 `accordion-content` 在掃描表裡是 BROKE_PAGE；照工廠要求的方式嵌套後能寫入、能渲染，**7 之 7**。註記現在就在那一列旁邊 |
| **瀏覽器** | 在 Chromium 三個視窗寬度上對兩個交付頁面做 3,988 次計算樣式讀取：2,929 條比對相符、912 條標為無法比對、**0 條被覆蓋** |
| **設計稽核** | 對比度、字體回退、CJK 字距、水平溢出、文字裁切、每行字數——在瀏覽器裡跑，**26 項發現，每一項都有書面裁定**——沒寫理由的 acknowledge 會被發布閘門拒絕 |
| **主題匯出／匯入** | 兩條路徑，都來回驗證過。`theme_export.php` 用 WP-CLI 把資料列搬成 JSON、ID 原封不動，副本送出的頁面逐位元組相同。`theme_zip.py` 走 Mosaic **自己**的 milestone 協定驅動 ZIP 匯出匯入——匯入預設進 test mode，要 `--activate` 才上線，因為它的預設是直接把 live 站切過去——並以 **22 項檢查**逐表、逐樹比對副本與來源：每張表相等、68,337 個節點 ID 保留、override 節點重新發 ID，唯一少的一列是走樹本來就不該帶的孤兒 |
| **線上量測** | 114 條 REST 路由、151 個 element class、59 個條件主體、23 張表 / 206 個欄位 |

`SKIPPED`、`NO_HOST`、`INCONCLUSIVE` 永遠不併進通過率。
**一支把自己的盲點算成成功的掃描工具，正是這個 skill 要反對的東西。**

### 動手之前值得先知道的兩個結果

**帶有 `group` 的屬性，單獨設定一律無效。** 兩個方向都精確：78 個無 group 的屬性得到
58 COMPILED、0 ABSENT；20 個有 group 的全部 0 COMPILED。所以 `borderLeftWidth`、
`outlineColor`、`gridColumnStart` 是**同一條規則的三個實例**，不是三個各自的怪毛病。
要用就用群組形狀——`border` 收 `{width, style, color}`——或者退回 `customStyles`。

**斷點覆寫只能「改變」屬性，永遠不能「移除」。** 窄螢幕的 `customStyles` 如果只是
沒寫某條框線，寬螢幕那條框線會活下來，在塌成單欄的版面正中間畫一條線。
**要把 `border-left:0` 明講出來。**

## 工具

```bash
wp eval-file tools/bootstrap_probe_theme.php          # 免授權的測試主題
python tools/build_site.py   --config c.json --site sites/moksa.json
python tools/verify_rwd.py   --config c.json --site sites/moksa.json --csv rwd.csv
python tools/copy_styles.py  --config c.json --from a --to-prefix b- --only "&._m"
wp eval-file tools/theme_export.php active > theme.json
wp eval-file tools/theme_import.php theme.json "名稱" rebind activate
```

`sites/_moksa.py` 是完整範例：一個真實工作室的首頁——刊頭、規格區塊、服務、九列作品表格、
流程、技術堆疊、產品、客戶見證、聯絡——**618 個節點全部透過資料表寫入**，
還有一個用具名 view timeline 做的、會跟著捲動的條款索引，完全沒有 JavaScript。

## 從哪裡開始讀

1. `references/data-model.md` —— 頁面到底住在哪裡。
2. `references/write-protocol.md` —— checkout / check / commit。
3. `references/failure-modes.md` —— Mosaic 怎麼壞的，都是量出來的。**動筆前先讀。**
4. `references/responsive.md` —— state / breakpoint / property 這個軸。
5. `references/styling.md` —— 一個樣式值怎麼變成 CSS。
6. `references/design-system.md` —— element class 與設計 token。

## 授權

MIT。Mosaic Pro 本身是有授權的第三方軟體，**不包含**在這個 repo 裡。
