# Mosaic's tutorials, mapped to headless builds

Mosaic publishes 24 tutorials: four under https://mosaicbuilder.com/docs/tutorials/
and twenty under https://mosaicbuilder.com/tutorials/ (basics, menus, interactions,
integrations - all of them listed in the site's `tutorial-sitemap.xml`; the index
pages load the list with JavaScript, so a plain fetch of them finds only four).
**None of the 24 uses custom code.** Several say so outright ("without writing any
JavaScript", "no code required"). That is the bar for this skill too - see "Native
first" in SKILL.md.

Status, per tutorial:

- **MEASURED** - built from `tools/interactions.py` by `tools/verify_recipes.py`
  and driven in Chromium (data/tutorial-recipes-verification.csv, 16 of 16).
- **PARTS** - every piece it uses is measured elsewhere in this skill; the
  tutorial as a whole has not been rebuilt.
- **OPEN** - at least one piece has not been driven headlessly yet. Named.

| tutorial | what it builds | status | how, headlessly |
|---|---|---|---|
| docs: dark-light-mode-switcher | site-wide mode toggle, remembered | MEASURED | second `collectionMode`, `mode_switch` on `document` + `set_cookie`, `pageLoad` gated by `cookie_is` |
| docs: loading-animation | full-page loader that fades out | MEASURED | fixed div, `data.hidden: true`, `pageLoad` opacity + `hide_at_end` |
| docs: reusable-animations | one scroll reveal reused by class | MEASURED | `elementScrollIntoView`, `trigger=class_target`, no target, `children` modifier; per-child delay with `tween(delay=)` |
| docs: animation-loop | endless vertical ticker, pause on hover | MEASURED (loop + hover pause) | `on(..., loop=True, ix_id=, out_of_view="1")`, hover `suspend`/`resume` by ID; the reposition tweens are `duration: 0` with a `delay` |
| interactions: reading-progress-bar | bar that fills while reading | MEASURED | sticky outer, `scrollIntoView` on the article targeting the bar, translateX `-100%` to `0%`, `progress=True, easing="linear"` |
| menus: off-canvas-menu | full-screen menu, hamburger/close | MEASURED (the toggle) | click `odd` slot: `display(start="flex")` + translateX `100%`>`0%`; `even`: back + `display(end="none")`; `data.hidden: true` on the panel; arrow-on-hover is a CSS state + `transition` |
| interactions: animated-shape-dividers | SVG divider that scales in and loops | PARTS | icon node with SVG, `transformOrigin`, `pageLoad` scaleY `70%`>`100%`, a second tween back, `loop=True` |
| interactions: background-clip | image through the letters | PARTS | `backgroundStyle` (clip text, fixed) + transparent `color`; references/styling.md |
| interactions: background-parallax | fixed section background | PARTS | `backgroundStyle` fixed |
| interactions: blurred-sticky-cta | frosted sticky button | PARTS | `position: sticky`, `bottom`, `backdropFilter`, background with alpha |
| interactions: flip-box-3d | card flips on hover | PARTS | `perspective`, `transformStyle`, back-face via `customDeclarations` (the tutorial does the same), hover `in`/`out` rotateY `180deg`/`0deg` on the wrapper |
| interactions: parallax-effect | rows drifting at two speeds | PARTS | `scrollIntoView` on the section targeting each grid, translateX `10%`>`-10%` and back; start/end via `settings` |
| interactions: scroll-timeline | sticky icons, fading rows, nested components | PARTS | `elementScrollIntoView` `in`/`out` slots, opacity and colour tweens with variables, sticky `top: 50vh`, nested Part components |
| interactions: video-controls | custom play / pause / overlay | OPEN (player actions) | click `odd`/`even`, opacity tweens, `player_play` / `player_pause` - their shape is read from the source, not driven yet |
| interactions: vimeo-hover-play | Vimeo plays on hover, pauses on leave | OPEN (player actions) | hover `in`/`out`, translateY overlay, `player_play`/`player_pause` |
| menus: mega-menu | dropdown with a component per item | OPEN (dropdown open-on-hover settings) | navbar > dropdown nodes (`mo.py placement`), a menu-item component, grid with an image |
| basics: layout-system | Section / Container / Row / Column / Grid / Div | PARTS | variants in `mo.py classes`; a node changes kind by its element class |
| basics: style-icons | library or pasted SVG icons, sized and coloured | PARTS | icon node, `currentColor`, colour variable |
| basics: context-bar | the editor's search bar | n/a | an editor UI feature; nothing to write |
| integrations: google-map | Google Maps element | PARTS | `googlemaps` node; the API key is a Mosaic setting the user enters |
| integrations: metabox | Loop over a CPT with Meta Box fields | PARTS | loop nodes and Meta Box variables, references/custom-fields.md; Order by "Publish date GMT" |
| integrations: webhook-setup | form posts to Zapier/Make | OPEN (webhook action not driven) | form node + a webhook form action; references/placement.md (forms) |
| integrations: mailchimp | form subscribes to Mailchimp | OPEN | form action with audience and field map; needs the user's API key |
| integrations: mailerlite | form subscribes to MailerLite | OPEN | form action; needs the user's API key |

What the measured ones settled that the tutorials leave implicit:

- The "HTML" element in the Navigator is the `document` node of the master; a
  variable-mode action there re-declares every variable of the collection on it.
- A suspend without an Interaction ID suspends every interaction on its target,
  including the hover that issued it - so "pause on hover" never resumes. Always pass
  the ID.
- `click` carries three slots at once - `click` (every click), `odd`, `even` - and
  the off-canvas toggle is odd/even on one interaction, not two interactions.
- A panel that starts `display: none` in its style can still be opened by a
  `display(start="flex")` action: the action wins for as long as it holds, and
  `display(end="none")` on the closing slot puts it back.
