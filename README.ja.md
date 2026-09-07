# mosaic-headless

[Mosaic Pro](https://mosaicbuilder.com)（Nextend）のサイトを、データモデルを直接書いて
構築・変更する — ビジュアルエディタも DOM も使わない。

*他の言語：[English](README.md) · [繁體中文](README.zh-TW.md) · [한국어](README.ko.md)*

---

Mosaic はページを **23 個のカスタムテーブル**に保持する。`post_content` でもなければ
`postmeta` でもない。要素ひとつにつき 1 行、ツリー構造は `parentID` カラム、兄弟の順序は
fractional-index の文字列。エディタはこのモデルの一クライアントにすぎない。
フォーマットそのものではないし、使う必要もない。

この skill はそのモデルの地図であり、**ソースを読んだものではなく、実際のインストールに
対して測定したもの**である。

## すべてに優先するただ一つの規則

**ノードタイプ、プロパティ名、列挙値、スタイルキー、Free/Pro の判断を記憶で書かないこと。
`data/` を引くこと。**

しかも grep ではなく `mo.py` で引く。grep は打った質問には答えるが、本当に抱えている
質問には答えない。`accordion-content` を grep すればその型が存在することは分かるが、
それを置くと commit は綺麗に通り、そのあと公開ページ全体が 54 バイトのエラー文字列に
なることは教えてくれない。

```bash
python tools/mo.py type accordion-content   # 1 つの型を、全ライブスイープに接続して表示
python tools/mo.py check div text button    # 危険な型・未知の型があれば exit 1
python tools/mo.py style --grouped          # 単独設定では必ず効かない 20 個
python tools/mo.py states --verified        # 実測でコンパイルされた状態だけ
```

そのうえでページを見る。Mosaic の失敗の仕方は 4 通りあり、
**HTTP ステータスが変わるのはそのうち 1 つだけ**：

```
バリデータによる正常な拒否   HTTP 200  + body に exceptions 配列
commit 中の PHP fatal        HTTP 500  （122 タイプ中 15、素の div の中でも起きる）
構造的に不正なノード         HTTP 200、コミット済み、DB に行もある。そして
                             公開ページ全体が 54 バイトのエラー文字列になる
値の「形」が違う             HTTP 200、保存される。ただし CSS ルールが存在しない
ルールは正しいが結果が違う   HTTP 200、スタイルシートにあり、内容も正しい。それでも
                             ブラウザは別の値を計算する
URL に対応するテンプレなし   HTTP 406、未ログインには空の body
```

**commit の成功も、正しいスタイルシートも、ページが動いている証拠にはならない。**

## 何を、どう検証したか

すべて実際のインストール上で実行 — WordPress 7.1、WooCommerce 11.1、Mosaic Pro 1.0.7、
**ライセンスなし**：ライセンスが制限するのはテーマライブラリと更新であってノードファクトリ
ではないため、Pro のタイプも登録され描画される。

| 対象 | 結果 |
|---|---|
| **ノードタイプ** | 122 / 122。1 ドキュメントにつき 1 タイプで commit → 描画 → 断言 → 削除。70 RENDERED、30 COMMITTED、15 COMMIT_5xx、7 BROKE_PAGE |
| **スタイルプロパティ** | 98 / 98 を実ページに書き、コンパイル済み CSS と照合：58 COMPILED、18 ABSENT、21 SKIPPED |
| **ノードプロパティ** | 181 / 181 を、各プロパティ自身の validator chain から導いた値で再測定：35 APPLIED、42 NO_EFFECT、55 NO_HOST、47 SKIPPED |
| **レスポンシブ** | 2 サイト計 667 件の `_t`/`_m` 宣言を、サイトが実際に配信したスタイルシートに対して 1 件ずつ断言 — 全件検証済み |
| **スタイル状態** | 53 状態のうち 52 を実ページに書き、テーブルが約束するセレクタと照合：**36 件が完全一致**、12 件 NO_HOST、3 件 SKIPPED、1 件 BROKE_PAGE。どの要素にも使えるグローバル 7 状態はすべて検証済み |
| **インタラクション** | JS アニメーション経路を、ネガティブコントロール付きで保存行を読み戻しながら検証：`propertyMetas` は**受理され保存される**。プロパティ値は依然としてバインドされないが、その境界は厳密になった |
| **入場アニメーション** | ページ読み込み後の 10 時点をサンプリングし 7 項目を断言 — 再生されること、アニメーションする `@property` カウンタが 100 に達すること、ベールがヒットテストから外れること、ビューポート内に opacity 0 のまま取り残された要素がないこと、実際のクリックが文書に届くこと、そして `prefers-reduced-motion` ではベールがそもそも存在しないこと |
| **ブラウザ** | 配信されたページを Chromium の 3 つのビューポートで計算スタイル 3,274 件読み取り：2,551 件が一致、723 件は比較不能として明示、**上書き 0 件** |
| **デザイン監査** | コントラスト、フォントフォールバック、CJK の字送り、横溢れ、テキストの切れ、1 行の文字数 — ブラウザ上で実行、**指摘 0 件** |
| **テーマの書き出し／読み込み** | 往復検証済み：テーマ全体を書き出し、コピーとして読み込み、そのコピーがバイト単位で同一のページを配信 |
| **実測** | REST ルート 114、element class 151、条件サブジェクト 59、23 テーブル / 206 カラム |

`SKIPPED`、`NO_HOST`、`INCONCLUSIVE` を合格率に混ぜることは決してしない。
**自分の死角を成功として数えるスイープこそ、この skill が反対しているものである。**

### 書き始める前に知っておく価値のある 2 つの結果

**`group` を持つプロパティは、単独で設定しても効かない。** 両方向とも厳密：group を持たない
78 個は 58 COMPILED / 0 ABSENT、group を持つ 20 個はすべて 0 COMPILED。つまり
`borderLeftWidth`、`outlineColor`、`gridColumnStart` は 3 つの別々の奇癖ではなく
**同一の規則の 3 つの実例**である。グループ形状を使うか（`border` は
`{width, style, color}` を取る）、`customStyles` に落とす。

**ブレークポイントの上書きはプロパティを「変える」ことはできても「消す」ことはできない。**
狭い画面の `customStyles` が単に境界線を書いていないだけなら、広い画面の境界線は生き残り、
1 カラムに畳まれたレイアウトの真ん中に線を引く。**`border-left:0` と明示すること。**

## ツール

```bash
wp eval-file tools/bootstrap_probe_theme.php          # ライセンス不要の作業用テーマ
python tools/build_site.py   --config c.json --site sites/moksa.json
python tools/verify_rwd.py   --config c.json --site sites/moksa.json --csv rwd.csv
python tools/copy_styles.py  --config c.json --from a --to-prefix b- --only "&._m"
wp eval-file tools/theme_export.php active > theme.json
wp eval-file tools/theme_import.php theme.json "名前" rebind activate
```

`sites/_moksa.py` が完全な実例：実在するスタジオのトップページ — マストヘッド、仕様ブロック、
サービス、9 行の実績テーブル、プロセス、技術スタック、プロダクト、推薦の声、連絡先 —
**618 ノードをすべてテーブル経由で commit**。名前付き view timeline で作った、スクロールに
追随する条項インデックスも含め、JavaScript は一切使っていない。

## どこから読むか

1. `references/data-model.md` — ページが実際にどこにあるか。
2. `references/write-protocol.md` — checkout / check / commit。
3. `references/failure-modes.md` — Mosaic の壊れ方、すべて実測。**書く前に読む。**
4. `references/responsive.md` — state / breakpoint / property という軸。
5. `references/styling.md` — スタイル値が CSS になるまで。
6. `references/design-system.md` — element class とデザイントークン。

## ライセンス

MIT。Mosaic Pro 自体はライセンス製品であり、この repo に**含まれていない**。
