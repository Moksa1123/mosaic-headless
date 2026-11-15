# Building pages, sites and themes

Moved out of SKILL.md on 2026-11-16 (skill SOP pass).

## Building a page

`tools/build_page.py` consumes a declarative spec and commits it through the verified
write path, refusing anything the tables say is unsafe. `tools/build_site.py` does the
same for a whole site: one master carrying the header and footer, one template document
per page.

The example page is deliberately varied rather than uniform: seven numbered clauses
in one rhythm, and then the things a document has that are NOT clauses - an
unnumbered plate, a capability table read as a grid, a figure drawn in hairline
boxes, a type specimen inverted onto the ink ground. The page changes ground five
times. A builder that can only produce one section shape has not been exercised.

**`sites/_moksa.py` is the worked example** - a real studio homepage (hero, statistics,
services, a nine-item work list, products, testimonials, CTA, footer) generated as a
spec and committed entirely through the tables. Read it for the shape of a real build:
the `bp()` breakpoint helper, the `code` node that carries the keyframes, the glass
header, and `apply_type()`.

A spec can carry a `theme` block, which is how a real site should be styled — design
tokens and element-class typography rather than per-node values:

```jsonc
"theme": {
  "variables": {"--brand": {"type": "color", "value": "rgb(13,108,102)"}},
  "variants": {"Heading 1": {"&": {"_": {"color": {"token": "--brand"}}}}}
}
```

`{"token": "--brand"}` anywhere in a style resolves to the `{"var": "<uuid>"}`
reference the compiler wants.

**Two brands in one theme need namespaced tokens and no variants at all.**
Collection variables and variants are both theme-global: two specs that each
declare `--ink` produce one `:root` with duplicate declarations, and two specs that
each style `Heading 1` produce one set of rules. Whichever committed last wins, for
every page. `sites/_moksa.py` namespaces its tokens (`--mk-*`) and bakes the type
system onto the nodes with `apply_type()` instead of using variants, which is
what lets it share an install with a completely different design.

Whole themes move between installs with `theme_export.php` / `theme_import.php`.
A theme is a themeID scattered across nineteen tables, and every one of them has a
COMPOSITE primary key of `(themeID, ID)` — so an import can keep every internal id
and rewrite nothing but the theme, which means no id remapping and nothing left
dangling. Round-tripped and verified: a full theme exported, re-imported as a copy,
and the copy served byte-identical pages.

Mosaic also has its own: `POST /theme/<id>/export` and `POST /theme/import/upload`
(or `/import/download` from a URL), plus `/duplicate` on themes, masters, templates,
components and style guides. The native export is a ZIP with the theme's
attachments inside, produced by a chunked, lock-protected milestone flow — you POST
repeatedly with `milestoneID` to step it through collect → compress → download — and
it is gated on admin capability only, not on a licence. It moves a whole theme, never
a single page. `tools/theme_zip.py` drives both directions from outside the editor.
Two things about the import that the route list does not tell you: with no
`themeActivateMode` it defaults to `live` and switches every visitor to the imported
theme (the tool sends `test` unless `--activate`). Test mode is per USER, not per
admin role: it is user meta `mosaic_<blogID>_test_mode_theme`, so the account whose
cookie made the import sees the imported theme on every later fetch while visitors
keep the live one - read a page logged out to see what visitors see; and a
milestone must be called until it answers `isCompleted:true` - stop one call early,
as the first version of the tool did after its last upload chunk, and that
milestone's batch bookkeeping is left in the lock for the NEXT milestone to read as
its own, which is how `extract` came to skip creating its directories and fail on
the first nested file with "Could not copy file".

Round-tripped and measured (`data/theme-zip-verification.csv`, 22 checks): export,
import in test mode, compare. Every scoped table equal; 68,337 of 68,337 nodes
outside overrides keep their ids; the 1,024 override nodes are re-keyed, with their
`originalID` re-pointed at the re-keyed component internals; the live theme
untouched. The node table came back one row short, and that row is the difference
between the two tools in one line: an orphan `div` with no parent, left by an
interrupted build, which a tree-walking import correctly does not carry and a
row-copying one (`theme_import.php`) would. `theme_export.php` exists because a
2 MB JSON of rows is easier to diff, version and reason about than a ZIP, and
because it needs nothing but WP-CLI; the ZIP is what the editor's buttons speak.

`copy_styles.py` pushes one node's style onto others by attrID or prefix, optionally
only certain `state.breakpoint` slices, and shows the diff before writing.

```bash
wp eval-file tools/bootstrap_probe_theme.php     # licence-free scratch theme
python tools/build_all.py --config sweep.json    # reset + build every design
```

Rebuilding a single page without a reset leaves an orphan template bound to the same
post — `build_all.py` resets first for that reason. `build_site.py` re-binds the post
to a fresh master and template and leaves the old pair bound to nothing; clear them
with `tools/prune_unbound.php` (dry run by default) after a batch of rebuilds.
