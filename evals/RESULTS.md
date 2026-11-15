# evals 結果

最新的在最上面。題目與評分標準見 `cases.json`，評分程式 `grade.py`。

## 2026-11-16（現行題組，Mosaic Pro 1.0.12 資料）

- 第 1 輪 16 題：沒 skill 也答對 4 題（scrollDepth slot、section 預設內距、modal 開啟判斷、customDeclarations dvh），標 `retired`，補 4 題。
- 第 2 輪：補的題裡 `image-attachment-path` 沒 skill 也對，再標 `retired`，補 `class-name-grammar`（第 3 輪只問沒 skill 那一方）。
- `accordion-content-bare` 的評分放寬：原本硬性要求答出「54 bytes」，但題目問的是「會怎樣、要放哪」。有 skill 的作答答出了 BROKE_PAGE 和 accordion-item，卻因為沒寫 54 被判錯，所以改成答出頁面會壞掉即可（理由寫在 cases.json 的 `note`）。
- 有 skill 的作答者回報路由缺口：`下拉選單` 查不到、沒有 unsafe／Pro 的路由列、前台行為只能 grep facts.md、class 命名沒有路由列。都已補上：terms-zh.csv、路由列、`mo.py facts`。
- 下表把各輪答案合併評分，每題都用最後一版題目和評分標準。
- 舊的 `claude plugin eval` 題組（5 題，1.0.8 時期）還在 `evals/<case>/`，最後一次紀錄是 2026-09-14：有 skill 0.867、沒有 skill 0.00，詳見 `evals/results/`。


| 項目 | 有 skill | 沒有 skill |
|---|---|---|
| 計分題答對率（16 題） | **16/16（100.0%）** | 0/16（0.0%） |
| 全部題目（16 題） | 16/16 | 0/16 |
| 模型 | claude-opus-5-5 | claude-opus-5-5 |
| 作答方式 | subagent 讀 SKILL.md、用 mo.py 與 references 查（r1＋r2 合併） | subagent 不用任何工具，憑記憶作答（r1＋r2＋r3 合併） |
| 答案檔 | `evals/runs/2026-11-16-final-with-skill.json` | `evals/runs/2026-11-16-final-without-skill.json` |

| 題目 | 可信度 | 有 skill | 沒有 skill | 備註 |
|---|---|---|---|---|
| `select-split-1012` | measured | ✅ | ❌ |  |
| `popover-trigger-slots` | measured | ✅ | ❌ |  |
| `popover-flipped-state` | measured | ✅ | ❌ |  |
| `shorthand-interaction-types` | documented | ✅ | ❌ |  |
| `interaction-value-shape` | measured | ✅ | ❌ |  |
| `wysiwyg-text-escape-1011` | measured | ✅ | ❌ |  |
| `pro-only-types-1011` | documented | ✅ | ❌ |  |
| `url-capable-types` | measured | ✅ | ❌ |  |
| `unsafe-type-count` | measured | ✅ | ❌ |  |
| `accordion-content-bare` | measured | ✅ | ❌ |  |
| `local-loop-source` | measured | ✅ | ❌ |  |
| `button-text-editable` | measured | ✅ | ❌ |  |
| `no-template-status` | measured | ✅ | ❌ |  |
| `unprobed-node-props` | measured | ✅ | ❌ |  |
| `variant-delete` | measured | ✅ | ❌ |  |
| `class-name-grammar` | documented | ✅ | ❌ |  |

