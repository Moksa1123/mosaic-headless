<h1 align="center">Mosaic Headless</h1>

<h3 align="center">Mosaic Pro 無編輯器建站工具</h3>

<p align="center">
  <strong>Measured data model · Guarded page builder · Delivered-page verifiers</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3-blue?style=flat-square&logo=python&logoColor=white" alt="Python 3">
  <img src="https://img.shields.io/badge/node-18_or_later-green?style=flat-square&logo=node.js&logoColor=white" alt="Node.js 18 or later">
  <img src="https://img.shields.io/badge/playwright-browser_verifiers-blueviolet?style=flat-square" alt="Playwright for the browser verifiers">
  <img src="https://img.shields.io/badge/WP--CLI-server_scripts-blue?style=flat-square&logo=wordpress&logoColor=white" alt="WP-CLI for the server scripts">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/node_types-134-success?style=flat-square" alt="134 node types">
  <img src="https://img.shields.io/badge/node_properties-120-success?style=flat-square" alt="120 node properties">
  <img src="https://img.shields.io/badge/style_properties-101-success?style=flat-square" alt="101 style properties">
  <img src="https://img.shields.io/badge/responsive_checks-733-blueviolet?style=flat-square" alt="733 responsive checks">
  <img src="https://img.shields.io/badge/self--tests-56-blueviolet?style=flat-square" alt="56 self-tests">
</p>

<p align="center">
  <a href="https://www.npmjs.com/package/mosaic-headless"><img src="https://img.shields.io/npm/v/mosaic-headless?style=flat-square&logo=npm" alt="npm version"></a>
  <a href="https://www.npmjs.com/package/mosaic-headless"><img src="https://img.shields.io/npm/dt/mosaic-headless?style=flat-square&label=downloads&color=cb3837" alt="npm downloads"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/Moksa1123/mosaic-headless?style=flat-square" alt="License"></a>
</p>

<p align="center"><strong>English</strong> · <a href="README.zh-TW.md">正體中文</a> · <a href="README.ja.md">日本語</a> · <a href="README.ko.md">한국어</a></p>

> This is an unofficial community project. It is not made by, endorsed by, or affiliated with Nextend, the maker of Mosaic Pro. Mosaic Pro is licensed third-party software and is not included here.

## What it does

Mosaic keeps a page in its own database tables, one row per element, not in `post_content`. This skill is a measured map of that model plus the tools to write through it, extracted from Mosaic Pro 1.0.14 and swept on a live site.

| Area | What you get |
|---|---|
| Lookup | `tools/mo.py`: 134 node types, 120 node properties, 101 style properties and 60 style states, each answered with its measured verdict; Chinese and colloquial words work (`mo.py css 內距`) |
| Build | `build_page.py` / `build_site.py` commit a page spec through Mosaic's REST write path and refuse what is measured to break the page |
| Verify | Chromium reads the delivered page: responsive rules, computed styles, menus, dialogs, sliders, forms |
| Move | whole themes exported and imported, Mosaic's data upgrades driven from outside wp-admin |
| Convert | Elementor pages turned into Mosaic specs, every unconverted element named |

### Look it up before writing

```bash
python tools/mo.py type accordion-content   # one type, joined to every live sweep
python tools/mo.py css 內距                  # Chinese works: padding-top/right/bottom/left
python tools/mo.py facts section padding     # measured front-end behaviour
```

### Build through the guard

```bash
python tools/mo.py skeleton > page.json
python tools/build_page.py --spec page.json   # refuses unsafe types, bad placement, out-of-enum values
```

### Check what visitors get

```bash
python tools/verify_rwd.py --site page.json       # every _t/_m declaration in the served stylesheet
python tools/verify_browser.py --site page.json   # what Chromium computes, plus a design audit
```

## When to use

Use it when the site runs Mosaic Pro and you want to build or change pages, templates, components, design tokens, popups, menus or interactions without opening the editor, or need to know exactly what a Mosaic setting does.

| Request | Go to |
|---|---|
| Elementor pages | `elementor-headless` |
| Block-editor (Gutenberg) pages | `gutenberg-headless` |
| SEO articles, Rank Math scores | `rankmath-seo-wp` |
| Site health checks, plugin updates, security | out of scope |

## Install

### Step 1: Pick an install method

Claude plugin (Claude Code; also from the Claude directory once listed):

```
/plugin install mosaic-headless --marketplace Moksa1123/mosaic-headless
```

npx, for Claude Code and other AI coding tools:

```bash
npx mosaic-headless@latest claude-code --global --force
npx mosaic-headless --list
```

Manual copy:

```bash
git clone https://github.com/Moksa1123/mosaic-headless.git
cp -r mosaic-headless ~/.claude/skills/mosaic-headless
```

| Platform | What is installed | Where |
|---|---|---|
| Claude Code | full skill: SKILL.md, references, tools, data, sites, evals, scripts | `~/.claude/skills/` or `./.claude/skills/` |
| Codex CLI | full skill | `~/.codex/skills/` |
| Gemini CLI | full skill | `~/.gemini/skills/` |
| GitHub Copilot | full skill | `./.github/skills/` |
| Cursor | one `.mdc` rule with the references embedded | `~/.cursor/rules/` |
| Windsurf | one rule file with the references embedded | `./.devin/rules/` |
| Continue | one rule file with the references embedded | `~/.continue/rules/` |
| Claude.ai | a zip to upload (SKILL.md, references, data, sites; no tools) | wherever you save it |

Requirements: Python 3 (lookup, build and self-test use the standard library only); Playwright for the browser verifiers (`requirements.txt`); WP-CLI on the server for the `.php` tools; Node.js 18 or later only for the npx installer. Works on Windows, macOS and Linux. A new npm version changes nothing until you re-run the installer with `--force`.

## Quick start

### Step 2: Query the data

```bash
python tools/mo.py check div text accordion-content
```

```
type               outcome     why
-----------------  ----------  -----------------------------------------------
accordion-content  BROKE_PAGE  AccordionItemElementMResource instance required
```

It exits 1: placed bare, that type commits and then turns the whole public page into an error string. `python tools/mo.py type accordion-content` says where it has to go instead.

### Step 3: Ask the assistant

- "Build a landing section on my Mosaic site: an H1, a paragraph and a button to /contact/."
- "Can I put an accordion-content directly inside a div in Mosaic?"
- "Add a popover tour with three steps that advances when each step closes."

## Trigger phrases

English: Mosaic Pro, Nextend, build a Mosaic page without the editor, Mosaic padding / hover / breakpoint, Mosaic popup, popover, modal, Mosaic interaction, move a Mosaic theme, Mosaic upgrade, Elementor to Mosaic.

中文：Mosaic、Nextend、不開編輯器做頁面、內距、外距、圓角、懸停、斷點、RWD、彈出視窗、浮動框、摺疊面板、頁籤、輪播、互動、動畫、搬佈景、Mosaic 升級、Elementor 轉 Mosaic。

## What it runs and connects to

- **Nothing runs on its own.** The plugin has no hooks, no MCP servers and no background processes. Tools run only when Claude follows `SKILL.md` and you approve the command.
- **Offline, local only**: `tools/mo.py` reads the CSV files in `data/` and prints answers. `tools/test_mosaic.py` and `tools/check_numbers.py` read the repository. They write nothing and contact nothing.
- **Your WordPress site, over its REST API**: `build_page.py`, `build_site.py`, `data_upgrade.py`, `theme_zip.py`, the `sweep_*.py` and `probe*.py` tools call Mosaic's REST routes on the one site you configure, to read and write pages, components, templates and themes. They contact only that site.
- **Your WordPress site, through WP-CLI**: the `tools/*.php` scripts run inside your WordPress with `wp eval-file`, on the server (usually over your own SSH). They read and write Mosaic's tables and theme data on that site. `prune_unbound.php` deletes data and runs as a dry run unless given the bare word `apply`; `theme_delete.php` deletes the theme you name and refuses the live one.
- **Reading your public pages**: `tools/verify_*.py` and `audit_mobile.py` open pages of that same site with Playwright (Chromium) or `urllib` and compare what was delivered with what was written.
- **Credentials**: a site URL, a WordPress logged-in cookie and the matching `wp_rest` nonce, for an administrator on your own site. `tools/mint_session.php` prints them on the server. Installed as a plugin, Claude Code asks for them as `userConfig` values; the cookie and nonce are marked sensitive and kept in the platform's credential store. They can also come from environment variables (`MOSAIC_SITE_URL`, `MOSAIC_REST_COOKIE`, `MOSAIC_REST_NONCE`) or a JSON file you pass with `--config`. **No tool looks for credentials on your machine.**
- **Third parties**: the worked example in `sites/` loads Google Fonts, so pages built from it make visitors' browsers fetch fonts from Google.
- Nothing is downloaded at install time, and no data is sent to the author or anyone else.

| Tool | Does | Touches |
|---|---|---|
| `mo.py` | query the measured surface, the front door | local `data/` only |
| `build_page.py` / `build_site.py` | commit a spec through the guarded write path | your site (REST) |
| `from_elementor.py` / `verify_conversion.py` | Elementor to Mosaic, and proof the content arrived | local file / your site |
| `verify_rwd.py`, `verify_browser.py`, `verify_*.py` | read the delivered page in Chromium | your site (read) |
| `theme_zip.py`, `theme_export.php` / `theme_import.php` | move a whole theme | your site (REST / WP-CLI) |
| `sync_nodes.py` + `list_bindings.php` | update a built site in place: only changed nodes, on the masters it already has; dry run unless `--apply` | your site (REST; bindings read with WP-CLI) |
| `data_upgrade.py` | run Mosaic's data migration after a plugin update | your site (REST) |
| `scan_inline_tags.py` / `fix_inline_tags.py` | find and fix text that prints HTML tags on 1.0.11+ | your site (REST) |
| `test_mosaic.py`, `check_numbers.py` | self-test and number check | this repository |

## How it's verified

Node types, node properties, style properties and style states are extracted from the plugin source (`tools/check_tables.py` re-extracts and diffs them), then written one at a time to a live install and asserted on the delivered HTML and compiled CSS. Each table below is in `data/`; the row count is checked by `tools/check_numbers.py`.

| Table | Rows | What was checked |
|---|---:|---|
| `data/node-verification.csv` | 134 | every node type committed alone and read back from the public page |
| `data/style-verification.csv` | 101 | every style property against the compiled CSS |
| `data/node-property-verification.csv` | 191 | each node property probed with a value its own validator accepts |
| `data/style-state-verification.csv` | 59 | each state matched against the selector it promises |
| `data/rwd-verification.csv` | 733 | every `_t` / `_m` declaration against the served stylesheet |
| `data/browser-verification/` | 4,132 | computed styles in Chromium at three viewports |
| `data/popover-verification.csv` | 37 | the popover: placement, closing, flip, chained tours |
| `data/menu-verification.csv` | 34 | hover dropdowns and phone menus with mouse, keyboard and touch |
| `data/form-surface-verification.csv` | 23 | every form field, including the buildable Select |
| `data/custom-fields-verification.csv` | 62 | ACF and Meta Box fields read through `@VAR` / `@LOOP` |
| `data/theme-zip-verification.csv` | 22 | Mosaic's own theme ZIP round-tripped and compared |
| `data/conversion-batch.csv` | 19 | every Elementor page of a site converted, built and checked |

- Self-test: `python tools/test_mosaic.py`, 56 offline tests (lookups, Chinese terms, the build output's shape and refusals, the public build interface, this repository's numbers and privacy).
- Evals: 16 questions about Mosaic 1.0.10 to 1.0.12 behaviour; with the skill 16/16, without it 0/16. Results: [evals/RESULTS.md](evals/RESULTS.md).
- Every number in `SKILL.md`, these READMEs and their badges is checked against the data by `tools/check_numbers.py`. Detail: [verification-record.md](references/verification-record.md).

What a lookup costs, priced with tiktoken on the same six tasks (`data/token-benchmark.csv`, measured when the tables were built; `tools/benchmark_tokens.py` reproduces it). Never load the tables; query them.

| `mo.py` commands | Read the source | Load every table | Query |
|---|---:|---:|---:|
| `params text ; params button ; prop url` | 10,005 | 259,539 | **961** |
| `style --grouped ; css border-left-width ; css border-radius` | 3,490 | 259,539 | **396** |
| `type accordion-content ; placement accordion-item` | 15,615 | 259,539 | **397** |
| `states --verified` | 3,619 | 259,539 | **1,054** |
| `css grid-column` | 1,862 | 259,539 | **51** |
| `stats ; check div text button accordion-content` | 63,172 | 259,539 | **288** |

## Limits

- Measured against Mosaic Pro up to 1.0.14. Features that live only in the 1.0.13 editor (new style-variable types, List classes, pageLoad delay and others) are not measured yet and are not written by the tools.
- Grid child placement properties emit nothing when written headlessly; some interaction shapes are still unmeasured.
- The browser verifiers need Playwright and a site you can write to; they are not part of the offline self-test.
- Open questions: [data/pending.csv](data/pending.csv). The long guide (failure modes, the Elementor converter, the worked example): [docs/guide.md](docs/guide.md).

## Repo layout

```
SKILL.md          what the assistant loads: sources, routing, tasks, verify
data/             measured tables (CSV), Chinese terms, pending list
references/       topic guides: data model, styling, dialogs, upgrades ...
tools/            mo.py, build and verify tools, WP-CLI scripts, self-test
sites/            the worked example as readable Python modules
evals/            graded questions and results
scripts/          installer and release gate
assets/           per-platform install templates
docs/             the long guide
.claude-plugin/   plugin and marketplace manifests
```

## License & author

MIT License. Made by Moksa ([moksaweb.com](https://moksaweb.com)). Issues: [GitHub](https://github.com/Moksa1123/mosaic-headless/issues).
