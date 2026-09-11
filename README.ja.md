# mosaic-headless

[![npm downloads](https://img.shields.io/npm/dt/mosaic-headless?label=npm%20downloads&color=cb3837)](https://www.npmjs.com/package/mosaic-headless)

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
質問には答えない。`accordion-content` を grep すればその型が存在することは分かる。
スイープ表は BROKE_PAGE だと言う — 置けば公開ページ全体が 54 バイトのエラー文字列に
なる。どちらも本当で、どちらも間違った答えだ。行の横の注記は、その文字列が「親がない」
ことを名指ししていること、`accordion > accordion-item` の下に入れ子にすれば commit も
描画も通り、キーボードで操作できる開閉 UI までついてくることを言っている。
`mo.py type` はその三つを一度に見せる。

```bash
python tools/mo.py type accordion-content   # 1 つの型を、全ライブスイープに接続して表示
python tools/mo.py check div text button    # 危険な型・未知の型があれば exit 1
python tools/mo.py style --grouped          # 単独設定では必ず効かない 20 個
python tools/mo.py states --verified        # 実測でコンパイルされた状態だけ
python tools/mo.py params text              # 1 つの型に設定できるものすべて
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
| **レスポンシブ** | 2 サイト計 731 件の `_t`/`_m` 宣言を、サイトが実際に配信したスタイルシートに対して 1 件ずつ断言 — 全件検証済み |
| **コンポーネント** | コンポーネント機構を端から端まで実行し **8 / 8**：カテゴリ配下に作成、ドキュメントを heal、書き込み可能な instance 経由でツリーを投入、読み取り専用の方は同じ書き込みを拒否（ネガティブコントロール）、最後に 2 つのインスタンスが 1 つの定義から描画 |
| **スタイル状態** | 53 状態のうち 52 を実ページに書き、テーブルが約束するセレクタと照合：**36 件が完全一致**、12 件 NO_HOST、3 件 SKIPPED、1 件 BROKE_PAGE。どの要素にも使えるグローバル 7 状態はすべて検証済み |
| **インタラクション** | JS アニメーション経路を、ネガティブコントロール付きで保存行を読み戻しながら検証：`propertyMetas` は**受理され保存される**。プロパティ値は依然としてバインドされないが、その境界は厳密になった |
| **入場アニメーション** | 単調時計でページ読み込み後の 15 時点をサンプリングし 8 項目を断言 — 再生されること、アニメーションする `@property` カウンタが 100 に達すること、ベールがヒットテストから外れること、ビューポート内に opacity 0 のまま取り残された要素がないこと、実際のクリックが文書に届くこと、`prefers-reduced-motion` ではベールがそもそも存在しないこと、そして全てが落ち着いた後もなお動いているものがあること。文書の初回レイアウトを待ってから始まるため、アニメーションの全くないページに対して遅れフレームは 1 つだけ |
| **常時アニメーション** | 隅で刷り続け、タップすると拡大する版 — **28 項目**：一時停止したタイムラインをスクラブして周期性を証明、5 つの幅 × 25 のスクロール位置でテキスト*と*操作要素の遮蔽を「決して読めない」を失敗条件として計測、ポインタでも Enter でも開くこと、reduced motion では静止すること。Mosaic 自身のアコーディオンの上に構築 |
| **アコーディオン** | `accordion-item` と `accordion-content` はスイープ表では BROKE_PAGE。ファクトリが要求する通りに入れ子にすれば commit も描画も通る、**7 件中 7 件**。注記はその行の横にある |
| **ブラウザ** | 配信された 2 ページを Chromium の 3 つのビューポートで計算スタイル 3,988 件読み取り：2,929 件が一致、912 件は比較不能として明示、**上書き 0 件** |
| **デザイン監査** | コントラスト、フォントフォールバック、CJK の字送り、横溢れ、テキストの切れ、1 行の文字数 — ブラウザ上で実行、**指摘 26 件、すべて理由付きで裁定済み** — 理由のない容認はリリースゲートが拒否する |
| **テーマの書き出し／読み込み** | 経路は二つ、どちらも往復検証済み。`theme_export.php` は WP-CLI で行を JSON として移し、id は不変、コピーはバイト単位で同一のページを配信。`theme_zip.py` は Mosaic **自身**の ZIP 書き出し／読み込みをそのマイルストーン・プロトコルで駆動する — 読み込みは `--activate` を付けない限りテストモードに入る、既定がライブサイトの切り替えだからだ — そして **22 項目**でコピーを元とツリー単位で突き合わせる：全テーブル一致、68,337 のノード id を保持、override ノードは再採番、足りない 1 行はツリー走査が運ぶべきでない孤児 |
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
