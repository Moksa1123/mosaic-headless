# mosaic-headless

Build and modify [Mosaic Pro](https://mosaicbuilder.com) (Nextend) sites by writing
the data model directly — no visual editor, no DOM.

*Read this in [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md)*

---

Mosaic keeps a page in **23 custom database tables**, not in `post_content` and not
in `postmeta`. One row per element, the tree carried by a `parentID` column, sibling
order by a fractional-index string. The editor is one client of that model. It is not
the format, and you do not need it.

This skill is the map of that model — measured against a live install rather than
read off the source.

## The one rule

**Never write a node type, property name, enum value, style key or Free/Pro claim
from memory. Look it up in `data/`.**

And look it up with `mo.py`, not grep. Grep answers the question you typed; it does
not answer the question you have. Ask grep about `accordion-content` and it confirms
the type exists. It does not mention that placing one commits cleanly and then
reduces the whole public page to a 54-byte error string.

```bash
python tools/mo.py type accordion-content   # one type, joined to every live sweep
python tools/mo.py check div text button    # exits 1 on an unsafe or unknown type
python tools/mo.py style --grouped          # the 20 that are inert set on their own
python tools/mo.py states --verified        # the states measured to compile
python tools/mo.py params text              # everything settable on one type
```

Then check the page. Mosaic has four failure modes and **only one of them changes the
HTTP status code**:

```
clean validator rejection   HTTP 200  + an `exceptions` array in the body
PHP fatal during commit     HTTP 500  (15 of 122 types do this from a plain div)
structurally invalid node   HTTP 200, committed, row in the DB, and the whole
                            public page becomes a 54-byte error string
wrong value SHAPE           HTTP 200, stored, and the CSS rule is simply absent
right rule, wrong result    HTTP 200, in the stylesheet, correct, and the BROWSER
                            computes something else
no template for the URL     HTTP 406 with an EMPTY BODY for anyone not logged in
```

A successful commit is not evidence of a working page, and neither is a correct
stylesheet.

## What was verified, and how

Everything ran against a live install — WordPress 7.1, WooCommerce 11.1, Mosaic Pro
1.0.7, **unlicensed**: the licence gates the theme library and updates, not the node
factories, so Pro types register and render regardless.

| pass | result |
|---|---|
| **node types** | 122 / 122 swept one per document, committed → rendered → asserted → deleted: 70 RENDERED, 30 COMMITTED, 15 COMMIT_5xx, 7 BROKE_PAGE |
| **style properties** | 98 / 98 written to a live page and checked against the compiled CSS: 58 COMPILED, 18 ABSENT, 21 SKIPPED |
| **node properties** | 181 / 181 re-probed with a value shaped by each property's own validator chain: 35 APPLIED, 42 NO_EFFECT, 55 NO_HOST, 47 SKIPPED |
| **responsive** | 688 `_t`/`_m` declarations across two sites asserted against the stylesheet the site actually served — all verified |
| **components** | the component system driven end to end, **8 of 8**: created under a category, document healed, tree filled through the writable instance, the read-only one refused the same write as a negative control, and two instances on a page rendering one definition twice |
| **style states** | 52 of the 53 states written to a live page and matched against the selector the table promises: **36 compiled exactly**, 12 NO_HOST, 3 SKIPPED, 1 BROKE_PAGE. All seven globally usable states verified |
| **interactions** | the JS animation path probed with negative controls and the row read back: `propertyMetas` **is** accepted and stored; the property values still do not bind, and the boundary is now exact |
| **entrance animation** | the page-load sequence sampled at ten timestamps and asserted on seven counts — it plays, its animated `@property` counter reaches 100, the veil leaves hit-testing, nothing in the viewport is stranded at opacity 0, a real click reaches the document, and under `prefers-reduced-motion` the veil never exists at all |
| **browser** | 3,637 computed-style readings on the delivered page in Chromium at three viewports: 2,725 compared and agreed, 912 not-comparable and labelled, **0 overridden** |
| **design audit** | contrast, font fallback, CJK tracking, overflow, clipped text, line measure — run in the browser, **0 findings** |
| **theme export/import** | round-tripped: a full theme exported, re-imported as a copy, and the copy served byte-identical pages |
| **measured live** | 114 REST routes, 151 element classes, 59 condition subjects, 23 tables / 206 columns |

`SKIPPED`, `NO_HOST` and `INCONCLUSIVE` are never folded into a pass rate. A sweep
that scores its own blind spots as successes is the thing this skill argues against.

### Two results worth knowing before you write anything

**A property that belongs to a `group` is inert when set on its own.** Exact in both
directions: 78 ungrouped properties gave 58 COMPILED and 0 ABSENT; all 20 grouped
ones gave 0 COMPILED. So `borderLeftWidth`, `outlineColor` and `gridColumnStart` are
three instances of one rule, not three oddities. Use the grouped shape — `border`
takes `{width, style, color}` — or `customStyles`.

**A breakpoint override can CHANGE a property but never REMOVE one.** Narrow-screen
`customStyles` that merely omits a border leaves the wide-screen border standing,
drawing rules down the middle of a collapsed layout. Say `border-left:0` out loud.

## Tools

```bash
wp eval-file tools/bootstrap_probe_theme.php          # licence-free scratch theme
python tools/build_site.py   --config c.json --site sites/moksa.json
python tools/verify_rwd.py   --config c.json --site sites/moksa.json --csv rwd.csv
python tools/copy_styles.py  --config c.json --from a --to-prefix b- --only "&._m"
wp eval-file tools/theme_export.php active > theme.json
wp eval-file tools/theme_import.php theme.json "Name" rebind activate
```

`sites/_moksa.py` is the worked example: a real studio homepage — masthead, spec
block, services, a nine-row work table, process, stack, products, testimonials,
contact — 618 nodes committed entirely through the tables, with a scroll-tracking
clause index built on named view timelines and no JavaScript.

## Where to start

1. `references/data-model.md` — where a page actually lives.
2. `references/write-protocol.md` — checkout / check / commit.
3. `references/failure-modes.md` — how Mosaic fails, measured. **Read before writing.**
4. `references/responsive.md` — the state/breakpoint/property axis.
5. `references/styling.md` — how a style value becomes CSS.
6. `references/design-system.md` — element classes and design tokens.

## Releasing

One command. The version lives in three places — `package.json`, the SKILL.md
frontmatter an agent reads, and the frontmatter each platform template writes on
install — and nothing keeps them together on its own.

```bash
npm version patch      # or minor / major
```

That runs, in order:

1. `preversion` → `bin/check-release.mjs`
2. npm bumps `package.json`
3. `version` → `bin/sync-version.mjs` writes the new number into SKILL.md and all
   eight platform templates, and stages them
4. npm commits and tags `vX.Y.Z`
5. `postversion` → pushes the commit and the tag

The tag push triggers `.github/workflows/release.yml`, which refuses to publish
unless the tag matches `package.json`, re-runs the release checks, proves the
installer runs, prints the tarball, then publishes with provenance and opens a
GitHub release.

`bin/check-release.mjs` is the gate, and it checks the things that are easy to get
wrong rather than the things that are easy to check:

- the three version numbers agree
- every glob in `files` matches something
- the row counts in the verification CSVs still equal the numbers SKILL.md quotes
- `SKIPPED` labels survive into the shipped data, because a sweep that hides its
  blind spots is the failure this skill argues against
- **the tarball itself is inspected**, not the intent. npm's `files` allowlist
  *overrides* `.gitignore`: naming a directory ships everything inside it, ignored
  or not. Listing `sites/` once put a real client's generator and content into the
  tarball — gitignored, and about to be published anyway.

Publishing runs on npm trusted publishing (OIDC): npm trusts this repository's
`release.yml` directly, so there is no token in the repository's secrets and
nothing to rotate. Provenance is attached automatically.

One-time setup, on npmjs.com under the package's Settings → Trusted Publisher:
publisher `GitHub Actions`, organisation `Moksa1123`, repository
`mosaic-headless`, workflow filename `release.yml`, environment name left
**empty** — the workflow declares no environment, and a value here that the run
does not match is refused. The connection cannot be edited afterwards, only
deleted and recreated.

## Licence

MIT. Mosaic Pro itself is licensed third-party software and is **not** included here.
