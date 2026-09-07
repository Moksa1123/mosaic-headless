# mosaic-headless

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
問它 `accordion-content`，它確認這個型別存在，但不會提到放一個下去會乾淨地寫入、
然後把整個公開頁面變成一段 54 bytes 的錯誤字串。

```bash
python tools/mo.py type accordion-content   # 一個型別，接上所有線上掃描結果
python tools/mo.py check div text button    # 型別不安全或不存在就 exit 1
python tools/mo.py style --grouped          # 那 20 個單獨設定必然無效的屬性
python tools/mo.py states --verified        # 實測會編譯出來的狀態
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
| **響應式** | 兩個站共 667 條 `_t`/`_m` 宣告，對照網站實際送出的樣式表逐條斷言——全數通過 |
| **樣式狀態** | 53 個狀態中的 52 個寫進真實頁面，對照表格承諾的選擇器逐一比對：**36 個完全吻合**、12 個 NO_HOST、3 個 SKIPPED、1 個 BROKE_PAGE。七個可用於任何元素的狀態全數驗證 |
| **互動動畫** | 帶負對照組並讀回儲存列來探測 JS 動畫路徑：`propertyMetas` **確實**會被接受並儲存；屬性值仍然無法綁定，但界線現在很精確 |
| **入口動畫** | 在載入後十個時間點取樣並做七項斷言——它有播、被動畫的 `@property` 計數器跑到 100、遮罩退出點擊判定、視窗內沒有任何內容卡在 opacity 0、真實點擊落在文件上，而在 `prefers-reduced-motion` 下遮罩根本不存在 |
| **瀏覽器** | 在 Chromium 三個視窗寬度上對交付頁面做 3,274 次計算樣式讀取：2,551 條比對相符、723 條標為無法比對、**0 條被覆蓋** |
| **設計稽核** | 對比度、字體回退、CJK 字距、水平溢出、文字裁切、每行字數——在瀏覽器裡跑，**0 項發現** |
| **主題匯出／匯入** | 完整來回驗證：匯出整個主題、以副本身分匯入，副本送出的頁面逐位元組相同 |
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
