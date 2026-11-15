# Tools and the session

Every tool in `tools/`, and where the REST session comes from. Moved out of SKILL.md on 2026-11-16 (skill SOP pass).

## Tools

| tool | does |
|---|---|
| `mo.py` | query the measured surface - **the front door** |
| `benchmark_tokens.py` | reproduce the token figures: source vs tables vs query, six tasks |
| `build_page.py` | commit one page spec through the verified write path |
| `build_site.py` | a whole site: one master with the shell, one document per page |
| `verify_rwd.py` | does every `_t`/`_m` declaration reach the served stylesheet? |
| `verify_browser.py` | does the **browser** compute what the stylesheet promised - and does the result pass a design audit? |
| `verify_intro.py` | does the page-load animation play, and - the part that matters - does it END and hand the page back? |
| `verify_menus.py` | build and drive every site-menu option: does hover hold, do the keyboard and a touch tablet work, does the phone drawer trap focus, close on Esc and stay above a sticky header? |
| `verify_loop.py` | a decoration that runs forever: does it loop (paused-timeline scrub), does it bury text or controls anywhere a reader can rest, does it open by pointer and by keyboard, is it still under reduced motion? |
| `probe_accordion.py` | the accordion family nested as its factory requires, plus the guard's refusal of the bare node - the probe that corrected two rows of this skill's own tables |
| `from_elementor.py` | an Elementor `_elementor_data` tree -> a Mosaic page spec, with every element it cannot convert reported by name and reason (`--strict` to refuse a lossy spec) |
| `inline_html.py` | an HTML fragment -> `text` / `list` nodes with `wysiwyg-span` / `-link` / `-linebreak` inside, for content that arrives as HTML (a 1.0.11 text run prints tags literally); `from_elementor.py` uses it |
| `verify_conversion.py` | did the conversion carry the page? every source string, image, link and heading level looked for on the delivered Mosaic page |
| `sweep_node_types.py` | commit every node type one per document and assert the delivered HTML |
| `sweep_style_properties.py` | write every style property and check the compiled CSS |
| `sweep_node_properties.py` | probe every node property with a value from its own validator chain |
| `sweep_style_states.py` | write every style state and check the selector it compiled to |
| `sweep_components.py` | build a component, instance it twice, and prove one definition served both |
| `sweep_interactions.py` | which interaction animation shapes survive to the frontend payload |
| `interactions.py` | a library, not a command: `tween`, `on`, `mode_switch`, `set_cookie`, `cookie_is`, `hide_at_end`, `suspend` / `resume`, `class_target` - every interaction shape in the form the editor stores |
| `verify_recipes.py` | builds Mosaic's four docs tutorials on one page and drives each in Chromium |
| `theme_export.php` / `theme_import.php` | move a whole theme across installs, ids intact |
| `theme_zip.py` | drive Mosaic's OWN export/import - the ZIP the editor makes, attachments included, over the milestone protocol; import lands in test mode unless told `--activate` |
| `theme_zip_compare.php` | hold an imported copy against its source, tree for tree - every scoped table, the (parentType, type) shape, which ids survive, and orphans named rather than counted |
| `prune_unbound.php` | delete the templates no post is bound to, the masters no kept template uses, their nodes, then orphan nodes pass after pass - one theme, dry run unless `--apply`, `assign="auto"` templates kept |
| `theme_delete.php` | remove a theme completely through the plugin's own routine; refuses the live one |
| `fix_text_runs.py` | wrap text runs that sit directly under a button, menu-link or other non-text element (built before v1.34.1) in an Inherited text `text` node, so the editor can edit them - every master, template and component, through each document's own commit; dry run unless `--apply`, idempotent, component overrides kept |
| `scan_inline_tags.py` | read only: list every `wysiwyg-text` run whose text holds HTML tags (printed literally on 1.0.11+), with the nearest attrID above it, across every master, template and component - run it before or after a site updates from 1.0.10; also warns on a document with more than one root |
| `fix_inline_tags.py` | rewrite those runs in place as `wysiwyg-span` / `-link` / `-linebreak` nodes (inline_html.py's mapping); a run that is one `<p>`/`<hN>` gives its tag to a text node that has none; lists, tables, images and mixed block/inline runs are skipped and listed; dry run unless `--apply`, idempotent |
| `verify_slider.py` | the slider in a real browser: does it advance, do the arrows and bullets drive it, does the keyboard, does it stop when motion is not wanted - `--label`/`--append` put several sliders in one table, which is where a carousel and a plain slider can be held against each other |
| `verify_navigation.py` | a multi-page site: is every menu item a real `<a href>`, does every page answer 200 (a template that was never bound answers 406 with an empty body, which only a logged-out visitor sees), and with `--viewports` does any page scroll SIDEWAYS - the one question no per-page checker asks - and whether every in-page `#fragment` resolves ON THE PAGE THAT CARRIES IT, which an HTTP check cannot see: a bare `#services` in a SHARED header fetches the current page, answers 200 everywhere, and does nothing on every page but the one that has that section |
| `verify_dialog.py` | the modal in a real browser (1.0.9 and 1.0.10 alike: open is read as `:popover-open` or `dialog.open`): does it open, close, answer Esc, remember, cap - and does an OpenStreetMap carry the coordinates it was given |
| `verify_popovers.py` | 1.0.10's popover in a real browser: opens, lands where its positioning says, blocks nothing, closes the way closedby says, flips, chains, and ends - every check reads `:popover-open`, never an attribute |
| `verify_dialog_lab.py` | the question after "does the modal work": can three nodes be made into a bottom sheet, a side drawer, a corner notice, a full takeover and a gate with no way out - and does each one still fit at phone width, which the page's own width check cannot see |
| `verify_tokens.py` | the design tokens as the BROWSER resolved them: every `:root` property declared once (a changed value does not retire the old one), non-empty, and actually pointed at by something - a wrong `skinsData` shape still emits the declaration and serves white |
| `verify_components.py` | presses the interactive components on a page and asserts the RESULT - a pane actually swapped, an accordion item actually opened, the map carries the coordinates it was given - because "these all work" is worth what the last press proved |
| `audit_mobile.py` | the RWD defects a sideways-scroll check cannot see - type under the legible floor, controls too small to hit, a grid that never collapsed, content escaping a box that is not clipping it - re-opened at every `--widths` |
| `list_fields.php` | every `@VAR` / `@LOOP` name Mosaic registers for one post - custom fields, their derived `__label` / `__url` / `__id` properties, the row variables of each loop - with the value each resolves to (`wp eval-file`) |
| `data_upgrade.py` | after a plugin update, run Mosaic's data migration over its own milestone route - the step wp-admin does from a screen - and set the config's version when the editor API is back |
| `copy_styles.py` | push one node's style onto others, by attrID or prefix |
| `bootstrap_probe_theme.php` | a licence-free scratch theme |
| `mint_session.php` | a matching cookie + `wp_rest` nonce from WP-CLI |
| `mosaic_config.py` | the one place a tool resolves the site URL and session - environment (`MOSAIC_SITE_URL` / `MOSAIC_REST_COOKIE` / `MOSAIC_REST_NONCE`) over `--config` file, so a credential never has to be written to disk |
| `check_tables.py` | re-extract all eleven source-derived tables and diff them against the shipped ones - the check for a table that is not wrong but STALE, which nothing else can see |

## The session, and where it comes from

Every tool that writes needs a site URL, a logged-in cookie and a matching
`wp_rest` nonce. **Never go looking for them on the user's machine** - not in a
browser profile, not in `wp-config.php`, not in a dotfile. Ask, or have the user
mint them:

```bash
wp eval-file tools/mint_session.php        # on the server, prints COOKIE= and NONCE=
```

Then either export them, which keeps the credential off disk entirely:

```bash
export MOSAIC_SITE_URL=https://example.com
export MOSAIC_REST_COOKIE='wordpress_logged_in_…=…'
export MOSAIC_REST_NONCE=0a0326da96
python tools/build_site.py --site sites/moksa.json
```

or pass a JSON file the user wrote:

```bash
python tools/build_site.py --config sweep.json --site sites/moksa.json
```

`tools/mosaic_config.py` is the single place that resolves this, and the
environment wins over the file. Installed as a plugin, the three values are
`userConfig` options - the cookie and the nonce `sensitive: true`, so Claude Code
masks them and stores them in the platform credential store rather than in
`settings.json`.
