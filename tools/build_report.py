#!/usr/bin/env python3
"""Assemble the Mosaic verification report as a single self-contained HTML page."""
import io
import json
import os

ROOT = r"C:/Users/yun19/OneDrive/桌面/mosaic"
SHOTS = json.load(io.open(os.path.join(ROOT, "shots/web/_embed.json"), encoding="utf-8"))
BASE = "https://woocommerce-1469814-6656199.cloudwaysapps.com"

PAGES = [
 dict(slug="brutalist", shot="01-brutalist", name="Brutalist Grid", nodes=21, bytes=31366,
      palette=["#f5f3ee", "#101010"],
      style="紙白底、墨黑字，唯一字族是 Courier New 等寬體。84px 標題 letter-spacing -4px 壓到幾乎相黏，line-height 0.88 讓兩行咬在一起。三張卡片用 3px 實心黑框直接相鄰、gap 為 0，邊框自己變成分隔線——沒有圓角、沒有陰影、沒有第三個顏色。",
      motion="hover 時整格背景由紙白翻成墨黑（<code>background-color</code>，200ms ease）。只有一個動畫，因為這個風格的主張就是「除了結構什麼都不要」。",
      components="<code>section</code> ×1、<code>div</code> ×4、<code>text</code> ×8（h1/p/h3）、<code>wysiwyg-text</code> ×8",
      props="20 個樣式屬性；<code>borderStyle</code> 物件（12 個 border 長寫）、<code>textTransform</code>、<code>letterSpacing</code>、<code>fontFamily</code>"),
 dict(slug="glass", shot="02-glass", name="Glassmorphism", nodes=21, bytes=31221,
      palette=["#2b1055", "#7597de", "#f2a1c4"],
      style="140° 三段線性漸層（紫→藍→粉）鋪滿整個 viewport，卡片是 14% 白 + <code>backdrop-filter: blur(16px)</code> 的霧面板，配 1px 半透明白邊界當邊緣光。深度來自模糊，不是陰影。標題用 300 字重的細體置中，跟厚重的漸層形成反差。",
      motion="hover：卡片上浮 10px（<code>translateY</code>），同時背景不透明度 0.14→0.24、模糊 16px→22px、邊界亮度提高，320ms ease 一起過渡。折射感是靠模糊半徑變化做出來的，不是靠位移。",
      components="<code>section</code> ×1、<code>div</code> ×4、<code>text</code> ×8、<code>wysiwyg-text</code> ×8",
      props="22 個；漸層與 backdrop-filter 走 <code>customStyles</code>，圓角走 <code>borderRadius</code> 結構化值"),
 dict(slug="editorial", shot="03-editorial", name="Editorial Serif", nodes=24, bytes=30758,
      palette=["#fcfbf7", "#1a1816", "#b03a2e"],
      style="雜誌內頁。Georgia 襯線體撐全場，72px 標題 400 字重（不是粗體）置中，副標用斜體。單一磚紅色只出現在 eyebrow 標籤和三個欄位小標，總共四次。三欄 46px 間距、17px 內文配 1.75 行高——是為了「讀」而不是「掃」而排的。",
      motion="沒有動畫。這是刻意的：編輯風格的權威感來自靜止與留白，加 hover 效果反而會削弱它。八頁裡有兩頁沒有任何動態，這也是設計決策的一部分。",
      components="<code>section</code> ×1、<code>div</code> ×5（含一條 1px 分隔線）、<code>text</code> ×9、<code>wysiwyg-text</code> ×9",
      props="23 個；<code>fontStyle: italic</code>、<code>letterSpacing</code> 3px 的全大寫標籤、<code>maxWidth</code> + auto margin 控制行長"),
 dict(slug="neobrutal", shot="04-neobrutal", name="Neo Brutalist", nodes=21, bytes=31865,
      palette=["#ffde59", "#ff6b6b", "#6ce0a8", "#96b0ff"],
      style="飽和到近乎刺眼的黃底，三張卡片分別是珊瑚紅、薄荷綠、藍紫。每張都有 3px 純黑外框、14px 圓角，以及 8px 位移、0 模糊的硬陰影——陰影是實心色塊而不是柔光，這是這個風格的簽名。78px 800 字重標題把版面壓住。",
      motion="hover：卡片上移 6px，同時硬陰影從 8px 推到 14px，180ms ease。位移和陰影同時變大，讓卡片看起來真的離開了頁面。這是 <code>boxShadow</code> 結構化陣列 + <code>transform</code> 陣列一起動的例子。",
      components="<code>section</code> ×1、<code>div</code> ×4、<code>text</code> ×8、<code>wysiwyg-text</code> ×8",
      props="22 個；<code>boxShadow</code>（type: outside）、<code>borderStyle</code>、<code>borderRadius</code>、<code>transform</code>、<code>transition</code> 五種結構化值全在這頁"),
 dict(slug="darkglow", shot="05-darkglow", name="Dark Glow", nodes=23, bytes=31114,
      palette=["#090b18", "#1b2a5e", "#6ee7ff"],
      style="1100×600 的徑向漸層從頂端中央往外散，深海軍藍收到近黑——一個漸層取代了整張 hero 圖。訊號色只有一個高彩度青色，用在 eyebrow 和三個卡片標題。卡片本身是 6%→2% 的白色線性漸層加 22% 藍紫邊界，在暗底上幾乎只看得到輪廓。",
      motion="hover：卡片上移 8px，同時長出 40px 模糊、-6px 內縮、55% 不透明度的藍色光暈，300ms ease。因為模糊半徑夠大而位移夠小，讀起來是「發光」不是「投影」。",
      components="<code>section</code> ×1、<code>div</code> ×4、<code>text</code> ×9、<code>wysiwyg-text</code> ×9",
      props="25 個；徑向漸層與卡片漸層走 <code>customStyles</code>，光暈走 <code>boxShadow</code> 結構化陣列"),
 dict(slug="swiss", shot="06-swiss", name="Swiss Grid", nodes=33, bytes=30403,
      palette=["#ffffff", "#0c0c0c", "#de1a1a"],
      style="純白、Helvetica、四欄 32px 溝槽。開頭一條 120×8px 的紅色實心橫槓，接著 90px 500 字重（中等，不是粗體）標題、letter-spacing -4px。四個欄位各自頂著一條 2px 黑色上緣線。紅色出現三次，全部是文字或那條槓，從不當背景。右側整欄留空是刻意的。",
      motion="沒有動畫。瑞士風格的秩序感建立在絕對靜止上——任何 hover 位移都會破壞網格的權威。",
      components="<code>section</code> ×1、<code>div</code> ×6（含紅槓與四個欄位）、<code>text</code> ×13、<code>wysiwyg-text</code> ×13",
      props="20 個；上緣線用 <code>customStyles: border-top</code>（因為只要單邊，用 borderStyle 物件要寫十二個鍵）"),
 dict(slug="motion", shot="07-motion", name="Motion Matrix", nodes=46, bytes=33615,
      palette=["#0e0e10", "#1c1c22", "#78b4ff"], shot2="07b-motion-hover-glow",
      style="近黑底上的 4×2 深灰磚陣列，這頁的目的就是把八種動畫並排放在同一個視覺條件下比較，所以靜態設計刻意壓到最低——同樣的圓角、同樣的內距、同樣的字級，只有動畫不同。",
      motion="八格各自動一種屬性：<b>Lift</b> translateY −14px、<b>Tilt</b> rotateZ 4deg、<b>Grow</b> scaleX 1.06、<b>Glow</b> 46px 模糊藍色光暈、<b>Skew</b> skewX 6deg、<b>Fade</b> opacity 1→0.45、<b>Round</b> 圓角 14px→40px、<b>Blur</b> filter blur 3px。全部走 <code>transition</code> 陣列，260–320ms ease。右側附圖是用真實指標 hover 在 Glow 格上截下來的。",
      components="<code>section</code> ×1、<code>div</code> ×9、<code>text</code> ×18、<code>wysiwyg-text</code> ×18",
      props="26 個；<code>transform</code> 四種型別（translateY / rotateZ / scaleX / skewX）、<code>boxShadow</code>、<code>opacity</code>、<code>borderRadius</code>、<code>filter</code>（走 customStyles）"),
 dict(slug="components", shot="08-components", name="Composite Components", nodes=58, bytes=35378,
      palette=["#f8f8fa", "#14141a"],
      style="安靜的淺灰底白卡，因為這頁的主體不是視覺而是結構——它測的是那些「巢狀寫錯就會把整頁弄死」的複合元件能不能正確組出來。三個區塊：手風琴、分頁、清單。",
      motion="手風琴 <code>animation: slide</code>、<code>openMode: single</code>、<code>firstOpened: 1</code>——展開收合由 Mosaic 自己的 Accordion.js 驅動，不是 CSS。分頁標籤 hover 有 180ms 背景過渡，active 分頁由 <code>___tab--active</code> 這個節點型別專屬 state 上色。",
      components="<code>accordion</code> ×1 →<code>accordion-item</code> ×3 →（<code>accordion-title</code> + <code>accordion-content</code>）、<code>tabs</code> ×1 →<code>tabs-menu</code>→<code>tabs-tab</code> ×2 / <code>tabs-content</code>→<code>tabs-tab-pane</code> ×2、<code>list</code>→<code>list-item</code> ×3",
      props="18 個；另用到 <code>openMode</code>、<code>animation</code>、<code>firstOpened</code>、<code>defaultTabIndex</code>、<code>listType</code> 五個 enum 節點屬性"),
]

CARDS = "\n".join("""
    <article class="spec" id="{slug}">
      <div class="shot"><img src="{img}" alt="{name} 測試頁截圖" loading="lazy">{img2}</div>
      <div class="body">
        <header>
          <div class="swatches">{sw}</div>
          <h3>{name}</h3>
          <a class="live" href="{base}/probe-{slug}/" target="_blank" rel="noopener">probe-{slug} ↗</a>
        </header>
        <dl>
          <dt>設計風格</dt><dd>{style}</dd>
          <dt>動畫</dt><dd>{motion}</dd>
          <dt>元件結構</dt><dd class="mono-ish">{components}</dd>
          <dt>樣式屬性</dt><dd class="mono-ish">{props}</dd>
        </dl>
        <p class="verified"><span>{nodes}</span> 個節點提交 · 交付 <span>{bytes:,}</span> bytes · 瀏覽器實拍</p>
      </div>
    </article>""".format(
        img=SHOTS[p["shot"]], base=BASE,
        img2=('<img src="%s" alt="Glow 格 hover 狀態，藍色光暈已展開" loading="lazy">'
              '<figcaption>hover：Glow 格的 46px 模糊光暈</figcaption>' % SHOTS[p["shot2"]])
             if p.get("shot2") else "",
        sw="".join('<i style="background:%s"></i>' % c for c in p["palette"]),
        **p) for p in PAGES)

HTML = """<title>Mosaic 無頭建站驗證</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;1,6..72,400&family=JetBrains+Mono:wght@400;500&display=swap">
<style>
  :root {
    --paper:#f5f6f4; --card:#ffffff; --ink:#14171a; --muted:#5c6668; --faint:#8a9294;
    --rule:#dfe3df; --accent:#0d6c66; --accent-soft:#e3efed; --warn:#a8442a;
    --display:'Archivo','Helvetica Neue',Arial,sans-serif;
    --body:'Newsreader',Georgia,'Times New Roman',serif;
    --mono:'JetBrains Mono',ui-monospace,'SF Mono',Menlo,monospace;
    --shadow:0 1px 2px rgba(20,23,26,.05), 0 8px 24px -12px rgba(20,23,26,.14);
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --paper:#0f1213; --card:#171b1c; --ink:#e6ebe9; --muted:#9aa5a4; --faint:#6d7877;
      --rule:#262c2d; --accent:#4cc4b8; --accent-soft:#12302e; --warn:#e08a6c;
      --shadow:0 1px 2px rgba(0,0,0,.4), 0 10px 28px -14px rgba(0,0,0,.7);
    }
  }
  :root[data-theme="dark"] {
    --paper:#0f1213; --card:#171b1c; --ink:#e6ebe9; --muted:#9aa5a4; --faint:#6d7877;
    --rule:#262c2d; --accent:#4cc4b8; --accent-soft:#12302e; --warn:#e08a6c;
    --shadow:0 1px 2px rgba(0,0,0,.4), 0 10px 28px -14px rgba(0,0,0,.7);
  }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--paper); color:var(--ink); font-family:var(--body);
         font-size:17px; line-height:1.7; -webkit-font-smoothing:antialiased; }
  .wrap { max-width:1080px; margin:0 auto; padding:56px 28px 96px; }
  h1,h2,h3 { font-family:var(--display); font-weight:600; letter-spacing:-.02em;
             text-wrap:balance; margin:0; }
  h1 { font-size:clamp(34px,5vw,52px); line-height:1.06; letter-spacing:-.035em; }
  .eyebrow { font-family:var(--mono); font-size:11.5px; letter-spacing:.18em;
             text-transform:uppercase; color:var(--accent); margin:0 0 14px; }
  .lede { font-size:19px; color:var(--muted); max-width:60ch; margin:18px 0 0; }

  .tally { display:grid; grid-template-columns:repeat(auto-fit,minmax(132px,1fr));
           gap:1px; background:var(--rule); border:1px solid var(--rule);
           border-radius:3px; margin:40px 0 8px; overflow:hidden; }
  .tally div { background:var(--card); padding:16px 18px; }
  .tally b { display:block; font-family:var(--display); font-size:27px; font-weight:700;
             letter-spacing:-.02em; font-variant-numeric:tabular-nums; }
  .tally span { font-family:var(--mono); font-size:10.5px; letter-spacing:.1em;
                text-transform:uppercase; color:var(--faint); }
  .tally .bad b { color:var(--warn); }
  .tally-note { font-size:14.5px; color:var(--faint); margin:12px 0 0; }

  h2 { font-size:15px; letter-spacing:.14em; text-transform:uppercase;
       font-family:var(--mono); font-weight:500; color:var(--faint);
       margin:64px 0 22px; padding-bottom:10px; border-bottom:1px solid var(--rule); }

  .spec { display:grid; grid-template-columns:minmax(0,420px) minmax(0,1fr); gap:30px;
          background:var(--card); border:1px solid var(--rule); border-radius:4px;
          padding:22px; margin-bottom:20px; box-shadow:var(--shadow); }
  .shot { display:flex; flex-direction:column; gap:8px; }
  .shot img { display:block; width:100%; height:auto; border-radius:2px;
              border:1px solid var(--rule); }
  .shot figcaption { font-family:var(--mono); font-size:10.5px; color:var(--faint);
                     letter-spacing:.06em; }
  .body header { display:flex; flex-wrap:wrap; align-items:baseline; gap:10px 14px;
                 margin-bottom:14px; }
  .body h3 { font-size:23px; }
  .swatches { display:flex; gap:4px; width:100%; }
  .swatches i { width:26px; height:7px; border-radius:1px;
                box-shadow:inset 0 0 0 1px rgba(128,128,128,.28); }
  .live { font-family:var(--mono); font-size:12px; color:var(--accent);
          text-decoration:none; border-bottom:1px solid transparent; }
  .live:hover, .live:focus-visible { border-bottom-color:currentColor; }
  dl { margin:0; display:grid; grid-template-columns:auto minmax(0,1fr);
       gap:9px 18px; align-items:baseline; }
  dt { font-family:var(--mono); font-size:11px; letter-spacing:.1em;
       text-transform:uppercase; color:var(--faint); white-space:nowrap; }
  dd { margin:0; font-size:15.5px; line-height:1.62; }
  dd.mono-ish { font-size:14px; color:var(--muted); }
  code { font-family:var(--mono); font-size:.86em; background:var(--accent-soft);
         color:var(--accent); padding:1px 5px; border-radius:2px; }
  dd.mono-ish code { background:none; padding:0; color:var(--ink); }
  .verified { font-family:var(--mono); font-size:11.5px; color:var(--faint);
              margin:16px 0 0; padding-top:12px; border-top:1px solid var(--rule);
              font-variant-numeric:tabular-nums; }
  .verified span { color:var(--ink); font-weight:500; }

  .notes { margin-top:16px; }
  .notes li { margin-bottom:11px; color:var(--muted); font-size:16px; }
  .notes b { color:var(--ink); font-weight:500; }
  .foot { margin-top:60px; padding-top:20px; border-top:1px solid var(--rule);
          font-family:var(--mono); font-size:12px; color:var(--faint); line-height:1.9; }
  a { color:var(--accent); }
  @media (max-width:820px) { .spec { grid-template-columns:1fr; } .wrap { padding:36px 18px 64px; } }
  @media (prefers-reduced-motion:reduce) { * { transition:none !important; animation:none !important; } }
</style>

<div class="wrap">
  <p class="eyebrow">Mosaic Pro 1.0.7 · 無授權 · WP 7.1 / Woo 11.1</p>
  <h1>八個測試頁，八種設計語言</h1>
  <p class="lede">每一頁都只靠 <code>mosaic-headless</code> skill 的資料表建成——查表決定用哪個節點型別、什麼可以放進什麼、樣式值該寫成什麼形狀，然後走 REST 提交，最後在真實瀏覽器裡拍下來。建得出來的地方證明表是對的；建不出來的地方就是表的破洞，都列在最後。</p>

  <div class="tally">
    <div><b>122</b><span>節點型別掃描</span></div>
    <div><b>70</b><span>渲染成功</span></div>
    <div class="bad"><b>22</b><span>放錯位置會炸</span></div>
    <div><b>98</b><span>樣式屬性</span></div>
    <div><b>53</b><span>樣式 state</span></div>
    <div><b>8</b><span>設計頁全數通過</span></div>
  </div>
  <p class="tally-note">節點掃描是逐型別單獨放上真站 → 提交 → 渲染 → 比對 attrID → 刪除，122 型跑滿。八頁共 247 個節點，全部第一次提交就渲染成功。</p>

  <h2>測試頁</h2>
  {cards}

  <h2>建構過程揭露的問題</h2>
  <ul class="notes">
    <li><b>網格靜默失效。</b><code>gridTemplateColumns</code> 接受 <code>"repeat(3, 1fr)"</code>、存進資料庫、然後編譯出<em>空</em>——三欄卡片全部塌成單欄。八頁都建完、第一張截圖出來才發現。這類「值的形狀錯了」不會有任何錯誤訊息。</li>
    <li><b>五種結構化值已破解。</b><code>borderRadius</code>、<code>transform</code>、<code>boxShadow</code>、<code>transition</code>、<code>borderStyle</code> 都不吃字串。<code>boxShadow</code> 的 <code>type</code> 必須是 <code>outside</code>／<code>inside</code>，寫 CSS 慣用的 <code>outset</code> 會靜默編譯成 <code>box-shadow:none</code>。</li>
    <li><b><code>canBeParentFor</code> 不是複合元件的權威。</b><code>accordion-item</code> 宣告只收 accordion-item，但它的 <code>getAccordionItemDefaultData()</code> 說要 title + content——而 title 正是 Accordion.js 綁點擊事件的元素。少了它，伺服器渲染乾淨無誤，瀏覽器 console 直接拋 <code>Cannot read properties of null</code>。</li>
    <li><b>Pro 型別不需要授權。</b><code>isLicenseActive: false</code> 但 48 個 Pro 型別照常註冊、照常渲染。授權擋的是主題庫和更新，不是 node factory。</li>
  </ul>

  <p class="foot">
    測試站 woocommerce-1469814-6656199.cloudwaysapps.com · 主題為腳本生成的免授權 fixture，可整體重置重建<br>
    建構工具 tools/build_page.py + build_all.py · 設計規格 designs/*.json · 截圖 Playwright 1440×900 full-page
  </p>
</div>
""".replace("{cards}", CARDS)

path = os.path.join(ROOT, "report.html")
io.open(path, "w", encoding="utf-8").write(HTML)
print("wrote %s (%d KB)" % (path, os.path.getsize(path)//1024))
