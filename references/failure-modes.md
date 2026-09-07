# How Mosaic fails, measured

## `$wpdb->insert()` casts any column named `ID` to an integer

WordPress hardcodes `'ID' => '%d'` in `$wpdb->field_types`, because `wp_posts.ID` is
an integer. Mosaic's `ID` columns are `varchar(36)` — UUIDs, and for breakpoints the
literals `_t` and `_m`.

So `$wpdb->insert($table, $row)` on a Mosaic table stores `_t` as `0`. It happened to
fail loudly here, because `_m` also becomes `0` and collides on the composite primary
key — on a table where only one row was affected it would have been silent.

Pass an explicit format array on every insert:

```php
$wpdb->insert($table, $row, array_fill(0, count($row), '%s'));
```

## WP-CLI eats `--flags` before your script sees them

`wp eval-file script.php --active` fails with *unknown --active parameter*: WP-CLI
parses anything `--`-prefixed as its own option. Script arguments must be bare
keywords — `wp eval-file script.php active`.

## An invalid `ordering` orphans the node, silently

`ordering` is a fractional-index STRING. Send something that is not one and the
commit returns **no exception** — and the row is stored with **both `ordering` and
`parentID` blanked**. The node has no parent, so it never renders, and anything you
were measuring through it reads as a clean negative.

Measured side by side in one commit, three sibling probes:

```
ordering "a6"    -> stored: ordering=a6  parentID=a2dd9602-...   renders
ordering "z000"  -> stored: ordering=''  parentID=''            orphan
ordering "z001"  -> stored: ordering=''  parentID=''            orphan
```

This cost a whole style-property sweep: 77 probes committed without error, none
rendered, and all 77 properties came back ABSENT — including `color` and
`paddingTop`, which the entire site is built on. The result looked like a finding.
It was the tool being broken.

Use `ordering_for()` in `tools/build_page.py`; never format your own. And when a
sweep returns a suspiciously total failure, check that the probes rendered before
believing the measurement — `sweep_style_properties.py` now exits rather than
reporting a run in which nothing rendered.

## Duplicate `ordering` among siblings drops nodes, silently

`ordering_for()` in `build_page.py` wraps after 62 entries, so `ordering_for(i % 62)`
hands two siblings the same index. Mosaic keeps one and discards the other without an
exception. A sweep of 79 probes left 39 nodes in the database and still printed a
result table.

For more than 62 siblings, generate your own monotonic index - `"a" + ALPHA[i // 62]
+ ALPHA[i % 62]` gives 3844 lexicographically ordered slots.

## A sweep must refuse a contaminated page

Probe ids from separate runs share an id space, and two runs can give the same id to
different node types - `np-101` was a `<select>` from one run and a `<div>` from the
next, on the same page. Every number read off that page was meaningless.

Worse, the cleanup query was `LIKE "%np-0%"`, which silently misses every id from
`np-100` up, so "0 remaining" was itself wrong. Match the stored shape:
`LIKE '%"attrID":"np-%'`.

`sweep_node_properties.py` now exits unless the page carries exactly the probes this
run planned, allowing for the ones whose own property relocates them out of the tree.

## heal() owns the body's children

Do not parent anything directly to a `body` node. `heal()` rebuilds the
body > three-div skeleton whenever it decides one is missing, and probes hung
straight off the body do not survive it. Attach to a div inside the body instead.

Every failure below was produced on purpose, on a live install, by the sweep in
`tools/sweep_node_types.py`. None of it is inferred from source.

## Mosaic does not validate placement at commit time

This is the fact that shapes everything else. Mosaic's commit endpoint will happily
store a node whose parent makes no structural sense. The rejection happens later, at
**render** — and it takes the entire page with it.

Placing `accordion-item` directly under a `div`:

```
commit  -> HTTP 200, syncResponseEnvelopes with action "create". The row is in the DB.
render  -> HTTP 200, 54 bytes, body: "AccordionElementMResource instance required"
```

Not a 500. Not a WordPress error page. A **200 with a plain string where the site used
to be**. Three of the 74 free types do this from a plain `div` parent:

| type | what the dead page says |
|---|---|
| `accordion-item` | `AccordionElementMResource instance required` |
| `accordion-content` | `AccordionItemElementMResource instance required` |
| `wysiwyg-variable` | `NodeMResourceFilterFunctionInterface parent is missing` |

The consequence for anything automated: **a successful commit is not evidence of a
working page.** Fetch the page and check its size after writing. A monitor that only
watches status codes will report a healthy site that is serving 54 bytes.

It also means a batch write is dangerous in a way it is not in Elementor or Gutenberg:
one bad node does not degrade its own corner of the page, it deletes the page. Write
one subtree, verify, then write the next.

## Some types kill the commit request itself

Five free types return **HTTP 500** from `/commit` when placed under a `div`:

```
component-instance   loop   loop-items   loop-pagination-numbers   loop-pagination-number
```

These are the types that require a resolved context — a component to instantiate, a
query to iterate — and the constructor throws before Mosaic can turn the problem into
a normal validation response. Nothing is written, so a 500 here is *safer* than the
silent 200 above, but it is still a PHP fatal in the error log rather than an
error message you can show a user.

`document` produced a 502 on one run and a 500 on another: the same fatal, sometimes
surfacing as a gateway timeout instead. Treat 5xx from `/commit` as one class.

## Validator rejections arrive as HTTP 200

Separate from both cases above: when Mosaic *does* reject a value cleanly, it answers
`RESTJSONExceptionEnvelope` — HTTP **200** with an `exceptions` array in the body.

```python
resp = commit(...)          # 200
resp["response"]["exceptions"]   # <- the actual verdict lives here
```

So there are three distinct outcomes and only one of them changes the status code:

| what happened | status | how you detect it |
|---|---|---|
| clean validator rejection | 200 | `exceptions` in the body |
| PHP fatal during commit | 500/502 | status code |
| structurally invalid node accepted | 200 | **nothing, until you fetch the page** |

## Commit has side effects beyond the rows you sent

The first commit against a fresh theme came back having created things nobody asked
for:

```
create breakpoint      _t
create breakpoint      _m
create collection      9083a14b-…
create collectionMode  9a674a81-…
create collectionSkin  e4beb80a-…
```

`heal()` runs as part of the commit path, so the response's `syncResponseEnvelopes`
can contain resources from managers you never touched. Read the whole envelope list
and take every revision in it — assuming the response only describes your own writes
will leave you holding stale revisions for the rest of the session.

Composite types heal aggressively too: a naive batch that placed all 74 types once
produced **802 node rows**, because types like `accordion` and `navbar` build their
required children on commit.

## `modified_gmt` is server-assigned

A record committed with `"modified_gmt": "2026-09-05 17:00:00"` came back stored as
`16:59:16`. The server overwrites it. Do not use a value you sent as a local cache key.

## A page cache turns "it worked" into "the node does not exist"

Not a Mosaic failure - a failure of *checking* Mosaic, and it produces the exact
result this skill exists to prevent: a confident negative about something that is
actually there.

Commit succeeds. `build_site.py` reports the byte size the renderer produced. Then
the verifier fetches the URL, a full-page cache in front of WordPress (Varnish on
Cloudways, or any CDN) answers with the pre-commit HTML, and every declaration on a
node you have just added comes back `no-element`. Measured on this install: the
builder saw 138878 bytes, `curl` on the same URL a second later got 136021, and
seven declarations on two brand-new grid wrappers were reported missing while the
wrappers were sitting correctly in the database and in the committed JSON.

The tell is the byte count: if the size the builder reports and the size you fetch
disagree, you are not looking at what you wrote.

**And the cache cuts the other way too, which is worse.** Once every tool in the
toolchain cache-busts, nothing is left looking at the page a visitor receives. A
build finishes, every check reports green - responsive verified, computed values
agreed, design audit clean, the entrance animation asserted on seven counts - and
the site is still serving the previous document to everybody. Measured here: a
visitor got 141,134 bytes with none of the new work in it while a cache-busted fetch
of the same URL gave 148,457. Nothing was wrong except that nobody had looked.

`build_site.py` now fetches each page twice at the end of the build, plain and
cache-busted, and says so when they disagree. It cannot purge the cache - that needs
credentials a build script has no business holding - but it must not be silent. Two
fetches of the same live page differ by a few hundred bytes anyway, since nonces and
ids regenerate per request, so the tolerance is proportional: natural variance
measured at 0.25%, a stale document at 5%.

`tools/verify_rwd.py` now appends a unique `_v=<ms>` query string and sends
`Cache-Control: no-cache` on every fetch, so the assertion is always made against the
document that was actually committed. Do the same in anything else that checks a page
- including a browser: hard-reload is not always enough, a query string always is.

## Changing a design token's VALUE leaves the old one in `:root`

A collection variable is a row, and a row is identified by its ID. If the writer
mints a fresh ID each run - which `build_page.py` did, because its `_varIDs` cache
starts empty every time - then changing a token's value does not change the token.
It adds a second one.

The rows hang off the theme's collection, and `build_site.py` makes a fresh master
per build while the collection persists, so nothing ever cleans them up. Both
declarations reach `:root` and the later one wins:

```css
:root{ ... --mk-faint: rgb(107, 109, 113); ... --mk-faint: rgb(160, 162, 168); ... }
```

Measured: after changing `--mk-faint`, a rebuild reported OK, the new variable
existed with the correct value, `verify_rwd.py` passed, and the page kept rendering
the old grey. Ten stale rows had accumulated across earlier builds. **Every
server-side check agreed with the intent and the page still disagreed** - only
`verify_browser.py`, reading the computed colour off the element, could see it.

The fix is that a token's row ID must be a function of its name -
`uuid5(VAR_NAMESPACE, "--mk-faint")` - so a rebuild rebinds the row instead of
adding one, plus a reap of anything on the collection claiming a managed custom
property under an ID we did not derive. Both are in `theme_records()`.

The general shape is worth remembering beyond tokens: **anything keyed by a random
ID that you write repeatedly will accumulate**, and duplicates in a cascade fail
silently in favour of whichever happens to be last.

## A declaration can be present, correct, and still wrong

The fourth failure mode in SKILL.md - "wrong value SHAPE, HTTP 200, and the CSS rule
is simply absent" - has a quieter sibling: the rule is *present*, the value is what
you asked for, and what the browser does with it is not what you meant.

Three ways, all measured on the example page:

- **The unit resolves against something you did not think about.**
  `letter-spacing: -0.035em` is a normal amount of tightening for a Latin display
  face. On a 62px headline it is -2.17px, and the headline was Chinese.
- **The face cannot render the text.** `font-family: 'Space Grotesk', 'Noto Sans TC'`
  is honoured exactly: Space Grotesk has no CJK coverage, so Han characters come from
  Noto Sans TC - while still carrying the tracking that was chosen for the Latin
  face. Nothing reports a fallback.
- **The property was never in play.** `display: inline-block` on a flex item is
  blockified by the spec. The declaration was in the stylesheet, correct, and
  computed to `block`.

None of these is visible to anything that reads the stylesheet, because the
stylesheet is right. `verify_browser.py` asks the element instead.

## Reproducing all of this

```bash
wp eval-file tools/bootstrap_probe_theme.php          # licence-free scratch theme
python tools/sweep_node_types.py --config sweep.json --setup
python tools/sweep_node_types.py --config sweep.json --sweep
```

The sweep is destructive by design and must only be pointed at a scratch site.
