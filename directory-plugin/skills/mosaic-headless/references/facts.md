# Facts worth knowing before you look anything up

> Directory edition: commands that mention `tools/` need the full edition (`npm` package `mosaic-headless`); this folder ships reference files only. The `wp` commands run on your WordPress host; how you reach it is up to you.

Platform and rendered-tag facts, each measured. Moved out of SKILL.md on 2026-11-16 (skill SOP pass); `mo.py` answers lookups, this file answers "why did that happen".

## Facts worth knowing before you look anything up

- **The REST namespace contains the plugin version** (`/wp-json/mosaic/v1.0.11`). Read
  it from `mosaicOptions.rest_api_url`, never hardcode. After a plugin update the
  editor namespace is GONE until the data upgrade has run; only
  `mosaic/<dataVersion>/<version>/upgrade` answers. `tools/data_upgrade.py`.
- **`ordering` is a fractional-index string**, not a number.
- **The tree is a `parentID` column**, not nesting. There is no page-level JSON blob.
- **Everything is scoped to a `themeID`**, breakpoints included.
- **A post is a target, not a container.** Templates bind to posts through
  `mosaic_template_assigns`; one template serves many posts.
- **Only `wp_mosaic_locks` existing** means a half-installed Mosaic. The other 22
  tables appear when an admin loads `/wp-admin/admin.php?page=mosaic`.
- **Commit has side effects.** `heal()` runs inside it and creates breakpoints,
  collections and child nodes you never sent. Take every revision in the response.
- **One root per document, or the document renders empty.** A second, empty
  `component-internal` (or master/template root) ordered first makes Mosaic render
  from it: every instance of that component prints nothing, and within a day the
  overrides that point into the real tree were gone with no master commit in
  between (90 on a live 1.0.11 site; restoring them alone changed nothing until the
  empty roots were deleted). Heal syncs an instance's overrides by walking the
  component from that first root (`keepOverrideNodesInSync`), and heal runs on
  front-end renders too. Health check, which must return no rows (group by `themeID` too: the
  same component ID in two themes is not a duplicate):
  `SELECT themeID, documentType, documentID, parentType, COUNT(*) n FROM wp_mosaic_nodes WHERE parentType IN ('master','template','component','componentDocument') GROUP BY themeID, documentType, documentID, parentType HAVING n > 1`.
  A node's `revision` is a time-based UUID (v1), so it dates when that root was
  written. Match that time against the access log. `build_site.py` stops and the
  fix tools skip a document with more than one root; `scan_inline_tags.py` warns.
  Reading every document over REST does not create roots (135 before and after a
  full scan on the demo site). Both creations traced so far came from the
  database failing under load: a MySQL restart on one site, a crawler driving a
  burst of fast HTTP 500s on another. Each time a front-end render's heal read the
  failed query as "no root" and wrote a new empty one, with no REST write in the
  log. A site that sees this needs the load handled (bot rate limits, MySQL
  capacity) as much as the roots repaired.

  **Why a lost connection becomes an empty root.** Found by the em925 site's
  session reading Mosaic 1.0.12 and WordPress (2026-11-18), re-read here against
  Mosaic 1.0.13 and WordPress 7.1.4:
  - every front-end render builds its document with `load()` then `heal()`, and heal
    may write (`Mosaic/Builder/AbstractDocument.php`, `createEditorInstance()` at line
    376, `load()` / `heal()` at 380-381 in 1.0.13 - the file is byte-identical to 1.0.12);
  - when the connection has gone away (errno 2006) and `check_connection()` cannot
    reconnect, `wpdb::query()` returns `false` WITHOUT setting `last_error`
    (`wp-includes/class-wpdb.php` lines 2282-2288 on 7.1.4), so `get_results()` hands
    back the empty `last_result` that `flush()` left (lines 1921-1927);
  - `MosaicDB::get_results()` treats an empty array with an empty `last_error` as
    success (`Mosaic/Database/MosaicDB.php` line 25; identical in 1.0.12 and 1.0.13),
    so "the database was unreachable" reads as "this document has no root", and heal
    writes a new empty one - with empty instance overrides beside it.
  The more nodes a page has, the more queries a render makes, and the more uncached
  bot traffic a site gets, the likelier it is. A small site is less likely to hit it,
  not immune.

  **Prevention, measured on one live site (2026-11-18):** block front-end writes to
  `wp_mosaic_nodes`. A `query` filter refuses `INSERT` / `REPLACE` / `DELETE` on that
  table during an ordinary front-end request, while `UPDATE` passes and wp-admin,
  admin-ajax, REST (the editor and these tools), WP-CLI and cron are untouched; form
  submissions live in another table and are untouched too. When it blocks, the page
  is marked uncacheable, logged and reported. Before switching it on, the site ran it
  log-only over 34 pages: a normal render made 0 writes to `wp_mosaic_nodes`, so
  blocking costs nothing. It is the lightest safe fix found so far and applies to any
  Mosaic site; whether a site installs it is that site's owner's decision. The
  implementation belongs to that site and is not shipped here - the description above
  is enough to write one (a must-use plugin with a `query` filter and a log-only
  switch).
- **Changing a component's roots or its node ids empties its instances' overrides
  everywhere else.** An instance in another document (a template, the master) keeps
  one override node per component node, and heal re-syncs those nodes to the
  component on the next render that touches them. When the component's root or
  internal ids changed, heal rebuilds each override as a shell -
  `{"override":{"originalID":"<new id>"}}` - and the instance's text, links and
  images fall back to the definition's. Measured twice:
  - 2026-11-17, a live site: two components' extra empty roots were deleted by hand;
    the first front-end requests afterwards turned every override of their instances
    in the master into shells, and the footer's links and the header's cards lost all
    their text and URLs until the overrides were rewritten.
  - 2026-11-04, the demo site: rebuilding a component (which re-keys its internals)
    turned all 70 override nodes of 7 instances in two older, unbound templates into
    shells, every one pointing at the component's new ids; the bound templates were
    rebuilt in the same run and kept theirs (which is why `build_site.py` rebuilds
    every page that uses a component together).

  So before deleting any root-type node (`master-root`, `component-internal`,
  `template-internal`) or rebuilding a component on a site with content:
  1. back up the whole node table: `wp db export pre-change.sql --tables=wp_mosaic_nodes`;
  2. export every instance of that component and its override nodes:
     `SELECT * FROM wp_mosaic_nodes WHERE parentType='override' AND parentID IN
     (SELECT ID FROM wp_mosaic_nodes WHERE type='component-instance/<componentID>')`;
  3. make the change, render the affected pages once, then run
     `wp db query < tools/override_health.sql`: an instance with `all_shells = 1` that
     was not all shells in the export lost its content - write it back from the
     export (`build_site.py`'s override pass, or the saved rows).
  `tools/override_health.sql` also lists duplicate override nodes. It is read only.
- **`modified_gmt` is server-assigned.**
- **Styling hangs on the generated `._<token>` class, not your `attrID`**, and the
  token (`_a`, `_b`, ... `_ba`: a base-38 per-document counter) is not stable. The
  sibling `m-<type>` class is (`m-div`, `m-text m-wysiwyg`, `m-menu-link`), and a
  variant that renders its name adds it (`m-heading-2`). Before 1.0.8 the same
  three were `M_EL4`, `M_EL_Div` and `M_EL_Text__Heading2`; state classes moved
  with them (`m-accordion-item--opened`, `m-menu-link--current`, `m-tab--active`).
  Any CSS you write against an emitted class is coupled to the plugin version.
- **`body{opacity:0}`** — the theme reveals itself from JavaScript. Screenshot tooling
  must let scripts run or it captures a blank page. The reveal waits for
  `DOMContentLoaded`, i.e. for every `defer` script, so deferring scripts blanks the
  page longer; `html body{opacity:1!important}` is safe and was worth 72 → 86 mobile
  (`references/styling.md`).
- **Two themes can carry the same name, and only the ACTIVE one is bound to
  anything.** Every write to `theme/<themeID>/...` succeeds against an inactive
  theme - master, nodes, components, tokens, all of it - and then
  `createManualTemplate` answers `Master not found`, because it resolves the theme
  from the request, not from your URL. Read the active theme's id off
  `wp theme list --status=active` (`mosaic-1-1-<themeID>`) before building.
- **Page caches stack.** The demo host ran Varnish AND Breeze; purging Varnish
  changed nothing because Breeze still had the old document. `build_site.py`
  fetches the plain URL and a cache-busted one at the same moment and reports
  STALE CACHE when they differ by more than a percent - believe it, then find
  every layer. `wp breeze purge --cache=all` was the one that mattered.
- **A `code` node is a wrapper, not a splice.** `insertLocation:"inPlace"` puts your
  markup INSIDE `<div class="m-code _x">`, one level down - so a sibling combinator
  from injected HTML to a Mosaic node never matches, and a control you inject has
  to be styled through its own ancestors or through `:has()`. The native accordion
  avoided the question entirely.
- **`section` arrives with 80px of top and bottom padding.** Measured on a node
  whose spec set neither; between a masthead and the block below it that is a
  160px hole. Set `paddingTop`/`paddingBottom` explicitly when a section's rhythm
  is meant to come from its contents.
- **A `code` node's content is a template, and `@media(` is a function call.**
  Mosaic parses `code` content for `@VAR(...)`; a CSS at-rule glued to its
  parenthesis - the form every minifier emits - is parsed as a call with
  unparseable arguments and the page renders as HTTP 500, after a clean commit.
  Write `@media (`. Text nodes are not parsed and are safe; measured both.
- **The front page 301s.** When a post is `page_on_front`, its own permalink
  (`/moksa/`) redirects to `/`; a fetch that does not follow redirects reads 0
  bytes and looks like an outage.
- **Every `build_site.py` run leaves a master behind, and they add up.** After a
  season of probing the test theme held 223 masters and 98,261 nodes with 25
  masters actually bound; Mosaic's ZIP import then spent 230s on masters and died
  in templates when nginx closed the upstream at five minutes. Pruned to the bound
  set (masters not reached from a bound template, their templates, their nodes)
  the same import took under two minutes and compared 22 of 22. Prune before you
  export - `wp eval-file tools/prune_unbound.php <themeID>` counts, `--apply` deletes; `wp_mosaic_template_assigns.parentID` -> template -> `masterID` is the
  bound set, plus any `assign="auto"` template. Then sweep ORPHANS: a probe run
  that half-failed, or a prune that removed a parent, leaves nodes whose parent id
  points at nothing. The export skips them, so the copy is short by exactly those
  rows and `theme_zip_compare.php` reports a tree that does not match - delete
  nodes with a missing parent REPEATEDLY until none are left, because each pass
  orphans the next level down.
- **`width` / `height` and their min/max take the keyword `stretch` since 1.0.9**,
  and Mosaic emits `-webkit-fill-available` before it so an older engine still gets
  something. They are still token-referencable - `CSSSizePropertyFactory` extends
  the collection-variable one, which is why `data/style-properties.csv` resolves a
  factory's ancestry rather than testing its name. 39 properties take a token, not
  the 34 counted before that fix.
- **A width copied out of Elementor needs `maxWidth: "100%"` beside it.**
  Elementor caps every widget with `max-width:100%`, so a px width there is a
  desktop intent its own CSS already constrains; carried across bare it keeps the
  full 600px and the page scrolls sideways on a phone. `verify_rwd` cannot see it
  - the declaration did reach the stylesheet - and nineteen converted pages were
  green on every per-page check while all nineteen overflowed at 390px.
- **Only three interaction types can be an `interactionShorthand`**: `pageLoad`,
  `exitIntent`, `scrollDepth` (`InteractionTypesManager::getShorthandInteractionTypes`).
  Any other is dropped in silence - the modal renders with its aria and its
  `closedby`, the page carries no interaction, and nothing ever opens it. The
  three that remain are exactly the ones that do not need the element to be
  visible first, which a modal never is.
- **A `slider-navigation-bullet` is a template, not a list item.** One authored
  bullet is repeated once per slide, every copy carrying the SAME id - writing
  three gets three templates and a document full of duplicate ids. The
  `aria-label` is Mosaic's, taken from each slide's own `title`. An arrow hides
  itself at the end it cannot pass unless the slider is a carousel, so a test
  that clicks `next` after autoplay has parked the slider finds nothing there.
- **An interaction that targets another element stores that element's NODE id**,
  not its attrID, so both have to be written in one pass (`nodeID` on a spec node
  pins it). The pin means "these two halves must agree", never "this uuid must be
  the one in the database" - `wp_mosaic_nodes`' key is `(ID, themeID)`, so a fixed
  id makes the spec single-use and the SECOND build dies on a duplicate key with
  the page half written. `build_page.refresh_node_ids()` now rewrites every pin and
  every reference to it at build time, so a spec with pins rebuilds as many times
  as you like.
- **Since 1.0.9 the three per-breakpoint stylesheets are one.**
  `mosaic-theme-document-styles-inline-css` carries the base rules and the
  `@media` blocks together; the old `mosaic-theme-block-editor-styles_<bp>-inline-css`
  ids are gone. And an element whose styles compile to nothing is emitted with
  no generated class at all, so "no `_token`" no longer means "did not render".
- **Since 1.0.10 the modal is a Popover-API host in the top layer.** `<dialog
  popover="manual">`; `dialog.open` is always false (read `:popover-open` or
  `data-mosaic-dialog-state`), the controller has `requestClose()` and no `close()`,
  and the closed state is `display:none !important` - so `display` on a modal host,
  a pin-it-open bug on 1.0.9, is safe now. z-index cannot put anything above it.
- **`popover` is the non-blocking dialog (1.0.10)**: no overlay, no children
  required, `closedby` defaults to `nothing`, `positioning` is `screen` (nine cells)
  or `element` (side / align / keepInView / anchor - no anchor = its trigger).
  Actions `popoverOpen` / `popoverClose` / `popoverToggle`; trigger `popover` with
  slots `show` / `beforeClose` / `afterClose`; style state `___popover--flipped`.
  **A dialog opened from inside another dialog is its child and closes with it, and
  closing a popover suspends the interactions inside it** - so a sequence advances
  on the step's own `afterClose`, never on a button that opens the next step.
  references/dialog-and-triggers.md
- **`scrollDepth`'s action slot is `reached` since 1.0.10** (plus `returned`). An
  action stored under the old slot name `scrollDepth` is kept and never runs.
- **A local-context loop's `loopSource` is `@VAR('post/<loop>')`, never `@LOOP()`.**
  Both render on the front end; `@LOOP` there throws in the editor
  (`_loopEvaluatorFunction is not a function`) and the canvas never finishes.
  `build_page.py` refuses it. `@LOOP(…)` inside text is fine.
- **A custom field is `@VAR('post/meta_<key>')`, and a multi-value one is a LOOP.**
  ACF and Meta Box both, plus bare post meta. Derived properties hang off the
  name with two underscores (`meta_k__label`, `__url`, `__id`); an ACF group is
  `loop-k` (hyphen) with `item/value_<sub>` rows; ACF puts the ID in a
  reference's primary slot where Meta Box puts the title. Run
  `tools/list_fields.php` on the post rather than guessing - a name it does not
  print does not exist. references/custom-fields.md
- **A variant row cannot be deleted, only emptied.** `status:"delete"` on a
  variant is accepted and ignored - the row is catalog-backed. Commit it back with
  `{"states": {"&": {"_": {}}}}` and the rule disappears; measured on Heading 2.
- **User class names have a grammar.** Variant sub classes and universal classes
  emit `[a-z0-9_-]` segments joined by `--` (`m-button--primary--sm`), each segment
  at most 60 characters, never starting with `_`, a digit or the reserved `m-`;
  names that do not sanitize fall back to `class`, and collisions get `-2`, `-3`.
  The emitted name is UNIQUE per theme (an `emittedName` column with a unique
  index on four tables), so two classes cannot share a spelling.

## Rendered-tag facts you would otherwise guess wrong

- **`button` renders three tags since 1.0.8, by two properties.** With a `url` it is
  `<a href>`; without one it is `<button type="button">` (1.0.7 emitted `<span>`);
  with `inactive:"1"` - the new integer-as-string property, the Badge variant's
  default - it is a `<span>`, a label rather than a control. Measured all three.
  `menu-link` and `wysiwyg-link` still render `<span>` without a `url`.
- **A button's words go in a `text` node, not straight under it.** The editor builds
  `button > text (Inherited text variant, 6381b2f3…) > wysiwyg-text`, and the same
  for menu-link, dropdown-toggle, tabs and submit labels. A `wysiwyg-text` placed
  directly under a button renders identically but cannot be edited in the editor:
  the navigator shows no child, and a double-click opens only the link settings.
  Only `text`, `label`, `choice-label`, `choice-legend`, `fieldset-legend` and the
  inline `wysiwyg-span` / `wysiwyg-link` hold runs directly. `build_page.py` wraps
  runs under any other type itself (`wrap_text_runs`), so the `"text"` shorthand is
  safe on a button, and a component's `text` override on a button follows the run
  down into that wrapper (`build_site.py`). Output: `<a class="m-button"><div class="m-inherited-text
  m-wysiwyg">…</div></a>` - the editor's own button carries the same `<div>`.
  A site built before v1.34.1 is fixed in place by `tools/fix_text_runs.py`
  (dry run, then `--apply`): measured on the test theme, 428 runs wrapped
  across its masters and templates, every page unchanged in text, a component instance's
  override still shown, and a second run finding nothing.
- **`text` renders as `<div>` by default** — set `tagName` for `<h1>`, `<p>` and so on.
- **A `wysiwyg-text` run prints no markup since 1.0.11.** Its `<` and `>` are escaped
  on output, so `A<strong>B</strong>C<br>D` reaches the page as those literal
  characters (measured: `A&lt;strong&gt;B&lt;/strong&gt;C&lt;br&gt;D`). Inline
  formatting is a node: `wysiwyg-span` → `<span class="m-span">` (style it),
  `wysiwyg-linebreak` → `<br>`, `wysiwyg-link` with `url` →
  `<a class="m-inline-link">`, each holding its own `wysiwyg-text` child. Entities
  still print as their character (`&lt;dialog&gt;` → `<dialog>`, `&amp;` → `&`).
  Bold and italic are NOT nodes but a property of the run: `wysiwyg-text` (and
  `wysiwyg-variable`) take `format: ["bold"]`, `["italic"]` or both, printed as
  `<strong>` / `<em>`. Both at once comes out misnested on 1.0.11 -
  `<strong><em> BI</strong></em>` (measured); browsers repair it, validators do not.
  `inline_html.py` maps `<strong>`/`<em>` to styled `wysiwyg-span`s instead.
  Through 1.0.10 the run was raw HTML instead, where a tag name in prose swallowed
  the rest of the paragraph; `build_page.py` refuses any tag in a run either way.
  **So a site built on 1.0.10 or earlier can start showing tags overnight**: the
  plugin updates itself, the data does not change, and every `<p>`, `<br>` or
  `<span>` written into a run now prints. Run `tools/scan_inline_tags.py` (read only)
  before or after the update, on any site not built by `build_page.py` (another
  converter, hand edits, an older helper). On the test theme it listed 179 runs on
  the Elementor-converted `el-*` pages, and each listed page printed `&lt;p&gt;` while
  the rest printed none. `tools/fix_inline_tags.py` then rewrites them in place
  (dry run, then `--apply`): 179 fixed, 0 skipped, a second run found nothing, no
  page printed a tag afterwards, and every page's visible text was identical.
  One layout change to expect: a run that was `<p>…</p>` used to put a real `<p>`
  inside the text node, and that `<p>` picked up the WordPress theme's own `p` rule
  (here `margin:24px 0 0; font-size:16px; line-height:24px`), overriding the node's
  own font size and line height. After the fix the node's own style applies, so
  each such block lost 8-49px of height. Giving the node `tagName: p` does not
  bring it back: Mosaic zeroes the margin on its own `p.m-text`.
- **`menu-link` is `width: fit-content` by default** (`.m-menu-link{display:flex;gap:4px;
  padding:4px 8px;width:fit-content;…}`). Used as a cell of a button row or a grid -
  a phone contact bar on `2fr 1fr 1fr` - its background hugs the text and the cell
  stays empty around it, whatever `display` or `justify-content` you give it. Set
  `width: 100%` on it (reported from a client build; the rule read from 1.0.10's
  `style.css`). The same rule's `align-items:center` matters when a `menu-link`
  wraps a whole card: set `alignItems: stretch` and `textAlign: left` on it.
- **`customDeclarations` is all or nothing, and its unit list is short.** The
  validator parses every declaration and drops the WHOLE block if one value fails.
  `!important` fails, and so does any unit outside `ValidatorCustomDeclarations`'s
  list - `dvh`, `svh`, `lvh`, `dvw`, container units: `height: 100dvh` takes every
  other line in the block with it, silently. The structured `height` / `maxHeight`
  fields do accept `dvh`.
- **`youtube` renders `<mosaic-youtube>` carrying `data-video-id`, `data-params`,
  `data-host`**, with the server's iframe inside `<noscript>`; the custom element
  builds the real iframe once it has a size. The iframe has no `title`, so an
  accessible name has to be added some other way. `youtubeUrl` is
  `{"v": "https://www.youtube.com/watch?v=…"}`; `lazyLoad` defers it and there is
  no click-to-load facade (same for `vimeo`). Sized by `width`/`height: 100%` inside
  an `aspect-ratio: 16/9` box. `privacy:"1"` switches the host to
  `www.youtube-nocookie.com` - measured on 1.0.11; the old NO_OUTPUT row was a probe
  artefact. `suggestedVideos` maps to `rel`. `vimeo`'s `privacy` is `dnt=1`.
- **Eight types emit custom elements**: `<mosaic-dropdown>`, `<mosaic-navbar>`,
  `<mosaic-tabs>`, `<mosaic-accordion>`, `<mosaic-vimeo>`, `<mosaic-youtube>` and
  friends. A selector written against `div`/`nav` misses all of them.
- **`icon` renders inline `<svg>`.**
- **Only four types take a `url`**: `button`, `menu-link`, `wysiwyg-link`,
  `dropdown-toggle`. Put one on a `text` or an `image` and it is accepted, stored,
  and emits no anchor whatsoever. To make anything else clickable, WRAP it in a
  `button` whose `style.variant` is the Link variant (`f671bc01-…`, `m-link`) - that
  is what the editor's "Wrap in link" writes, `button` takes children, and with a
  `url` it renders `<a class="m-link" href>` around them (measured on 1.0.11). A
  `menu-link` wrapper works the same way (`target="_blank"` included; probed) but
  carries menu styling. A `button` with `inactive` on keeps its `url`/`target`/`rel`
  stored and emits none of them.
- **An image's attachment-protocol path is relative to the UPLOADS directory.**
  `wp-attachment://image/<id>/<size>/2026/09/pic.png` resolves, and carries the
  attachment's `width`/`height` onto the tag. Give it the full
  `wp-content/uploads/2026/09/pic.png` - the obvious guess - and Mosaic prefixes
  the uploads base a second time, serving a broken `src` with no error and no
  dimensions. A plain `https://` URL also works, and is the right fallback for an
  image that is not an attachment on this site.

## Measured on a second site (Mosaic 1.0.13 + WooCommerce 11.3, 2026-11-20)

A store's Mosaic conversion, measured on its staging copy by that site's own session
(2026-11-20/21) and handed to this skill. Each line says what was also checked here
against the 1.0.13 source or this skill's tables; the rest is that site's measurement.

- **A WordPress menu nests through local-context loops, one namespace per level.**
  `wp-menu` sub-menus are a loop with `loopType: localContext` and
  `loopSource: @VAR('<parent namespace>/loop')`, and every level needs its own
  `loopNamespace` (`m2`, `m3`, `m4`...). Without one, an inner level reads the outer
  level's values: one menu came out as 4,227 duplicate links and a 6-second page.
- **A `list` cannot hold a `wp-menu`.** `list` accepts only `list-item` and
  `list-loop-items` (also `data/placement-rules.csv`), and `build_page.py` refuses it.
  Wrap the `wp-menu` in a `div` with `tagName: "ul"`; the output is a proper
  `ul > li`.
- **`loop-items` arrives as a three-column grid with an 80px / 32px gap**
  (`.m-loop-items{display:grid;grid-template-columns:1fr 1fr 1fr;gap:80px 32px}` in
  the 1.0.13 stylesheet). Set `rowGap` and `columnGap` yourself on every nested loop.
- **There is no `flex` shorthand key** (only `flexDirection`, `flexWrap`,
  `flexSizing`, `flexBasis`; `build_page.py` refuses `flex`). `display: list-item` was
  refused on that site, and `list-item` renders `display:flex` with no bullet: put
  either in `customDeclarations`.
- **`modal-window` arrived with 32px of padding** on that site. The 1.0.13 base
  stylesheet gives `.m-modal-window` none, so it comes from the node's default style,
  not from the stylesheet: set `padding*` when the window should be flush.
- **The accordion does not animate unless told to.** The panel jumps from 0 to full
  height; `data.animation: "slide"` animates it (`accordion`'s `animation` takes
  `none|slide`, `data/node-properties.csv`).
- **A server condition's `regexp` can exclude pages**: a negative look-ahead such as
  `/^(?!(452|28786)$)/` means "not these post ids" (`regexp` is an operator of the
  `text` comparator, `data/condition-comparators.csv`).
- **An image can name its thumbnail size**: `{"v": "@attachment(17321, '1536x1536')"}`
  (`attachment` takes two arguments, `data/evaluator-functions.csv`).
- **No action closes a dropdown.** The close actions are `modalClose` and
  `popoverClose` (and `popoverToggle`), so a phone sub-panel with a "back" button
  cannot be built from dropdowns alone; build it from a modal or a popover.
- **`dropdown-wrapper-wide` works inside a modal** with `position: fixed` (left 520px,
  top 0, height 100vh), and the pointer moving into the panel does not close it. Two
  traps, both met on that site and fixed there:
  - its default `clip-path: inset(0px -40px -40px -40px)` (in the 1.0.13 stylesheet)
    clips a `position: fixed` panel inside it;
  - in hover mode, leaving uses the convex hull of the toggle and the dropdown box as
    a safe area; a full-height box takes the links above and below into that hull,
    and hovering them does not close the dropdown.
  Fix: shrink the dropdown box to a zero-width anchor and put the panel in a fixed
  child.
- **An ACF field reads empty where its field group's location rule does not apply**:
  `@VAR('post/meta_x')` is empty on that page even though the post meta has a value.
  Check the group's location rules before suspecting the expression.
- **Never give a node inside a loop an `attrID`**: every repetition prints the same
  id.
- **`wp media regenerate` deletes the old thumbnails by default**, so a page that
  hard-codes an old thumbnail URL breaks; pass `--skip-delete`. Files WP-CLI writes
  belong to the user that ran it: reset the owner and permissions afterwards. This is
  WordPress, not Mosaic, and matters because Mosaic pages often carry thumbnail URLs.
