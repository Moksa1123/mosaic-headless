# mosaic-headless

Build and modify Mosaic Pro (Nextend) WordPress sites by writing the data model directly: no visual editor, no DOM, every lookup answered from measurements on a live install.

[![npm](https://img.shields.io/npm/v/mosaic-headless?style=flat-square)](https://www.npmjs.com/package/mosaic-headless)
[![License: MIT](https://img.shields.io/github/license/Moksa1123/mosaic-headless?style=flat-square)](LICENSE)

[正體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

> This is an unofficial community project. It is not made by, endorsed by, or affiliated with Nextend, the maker of Mosaic Pro. Mosaic Pro is licensed third-party software and is not included here.

## What it does

Mosaic keeps a page in its own database tables, one row per element, not in `post_content`. This skill is a measured map of that model plus the tools to write through it.

- **Look it up instead of guessing**: `tools/mo.py` answers what a node type, property, style key or state is called, what value shape it takes, where it may go, and whether it is safe. The data covers 134 node types, 120 node properties, 101 style properties and 60 style states, extracted from Mosaic Pro 1.0.13 and swept on a live site.
- **Chinese and colloquial words work**: `mo.py css 內距` finds padding; the terms follow Mosaic's own zh_TW strings.
- **Build pages and sites**: `build_page.py` and `build_site.py` commit a page spec through Mosaic's REST write path and refuse what is measured to break the page.
- **Check the delivered page**: verifiers read the public page in Chromium (responsive rules, computed styles, menus, dialogs, sliders, forms) instead of trusting the commit.
- **Move and convert**: export and import whole themes, drive Mosaic's data upgrades, and convert Elementor pages into Mosaic.

## When to use

Use it when the site runs Mosaic Pro and you want to build or change pages, templates, components, design tokens, popups, menus or interactions without opening the editor, or need to know exactly what a Mosaic setting does.

Do not use it for other builders: Elementor pages go to `elementor-headless`, block-editor pages to `gutenberg-headless`, SEO articles to `rankmath-seo-wp`. It does not do WordPress site health checks, plugin updates or security work.

## Install

Claude plugin (Claude Code; also from the Claude directory once listed):

```
/plugin install mosaic-headless --marketplace Moksa1123/mosaic-headless
```

npx, for Claude Code and other AI coding tools (Cursor, Codex CLI, Gemini CLI, Copilot, Continue, Windsurf, a Claude.ai upload zip):

```bash
npx mosaic-headless@latest claude-code --global --force
npx mosaic-headless --list
```

Manual copy:

```bash
git clone https://github.com/Moksa1123/mosaic-headless.git
cp -r mosaic-headless ~/.claude/skills/mosaic-headless
```

Requirements: Python 3 (the lookup, build and self-test tools use the standard library only); Playwright for the browser verifiers (`requirements.txt`); WP-CLI on the server for the `.php` tools; Node.js only for the npx installer. Works on Windows, macOS and Linux. A new npm version changes nothing until you re-run the installer with `--force`.

## Quick start

Ask the assistant, for example:

- "Build a landing section on my Mosaic site: an H1, a paragraph and a button to /contact/."
- "Can I put an accordion-content directly inside a div in Mosaic?"
- "Add a popover tour with three steps that advances when each step closes."

Or query the data yourself:

```bash
python tools/mo.py check div text accordion-content
```

```
type               outcome     why
-----------------  ----------  -----------------------------------------------
accordion-content  BROKE_PAGE  AccordionItemElementMResource instance required
```

It exits 1: placed bare, that type commits and then turns the whole public page into an error string. `python tools/mo.py type accordion-content` says where it has to go instead.

## Trigger phrases

English: Mosaic Pro, Nextend, build a Mosaic page without the editor, Mosaic padding / hover / breakpoint, Mosaic popup, popover, modal, Mosaic interaction, move a Mosaic theme, Mosaic upgrade, Elementor to Mosaic.

中文：Mosaic、Nextend、不開編輯器做頁面、內距、外距、圓角、懸停、斷點、RWD、彈出視窗、浮動框、摺疊面板、頁籤、輪播、互動、動畫、搬佈景、Mosaic 升級、Elementor 轉 Mosaic。

## What it runs and connects to

- **Nothing runs on its own.** The plugin has no hooks, no MCP servers and no background processes. Tools run only when Claude follows `SKILL.md` and you approve the command.
- **Offline, local only**: `tools/mo.py` reads the CSV files in `data/` and prints answers. `tools/test_mosaic.py` and `tools/check_numbers.py` read the repository. They write nothing and contact nothing.
- **Your WordPress site, over its REST API**: `build_page.py`, `build_site.py`, `data_upgrade.py`, `theme_zip.py`, the `sweep_*.py` and `probe*.py` tools call Mosaic's REST routes on the one site you configure, to read and write pages, components, templates and themes. They contact only that site.
- **Your WordPress site, through WP-CLI**: the `tools/*.php` scripts run inside your WordPress with `wp eval-file`, on the server (usually over your own SSH). They read and write Mosaic's tables and theme data on that site. `theme_delete.php` and `prune_unbound.php` delete data and run as a dry run unless told `--apply`.
- **Reading your public pages**: `tools/verify_*.py` and `audit_mobile.py` open pages of that same site with Playwright (Chromium) or `urllib` and compare what was delivered with what was written.
- **Credentials**: a site URL, a WordPress logged-in cookie and the matching `wp_rest` nonce, for an administrator on your own site. `tools/mint_session.php` prints them on the server. Installed as a plugin, Claude Code asks for them as `userConfig` values; the cookie and nonce are marked sensitive and kept in the platform's credential store. They can also come from environment variables (`MOSAIC_SITE_URL`, `MOSAIC_REST_COOKIE`, `MOSAIC_REST_NONCE`) or a JSON file you pass with `--config`. **No tool looks for credentials on your machine.**
- **Third parties**: the worked example in `sites/` loads Google Fonts, so pages built from it make visitors' browsers fetch fonts from Google.
- Nothing is downloaded at install time, and no data is sent to the author or anyone else.

## How it's verified

- Node types, node properties, style properties and style states are extracted from the plugin source (`tools/check_tables.py` re-extracts and diffs them), then written one at a time to a live install and asserted on the delivered HTML and compiled CSS.
- The demo pages are re-read in Chromium: 733 responsive declarations checked against the served stylesheet and 4,132 computed-style readings at three viewports. Details: [verification-record.md](references/verification-record.md).
- Self-test: `python tools/test_mosaic.py`, 42 offline tests (lookups, Chinese terms, the build output's shape and refusals, the public build interface, this repository's numbers and privacy).
- Evals: 16 questions about Mosaic 1.0.10 to 1.0.12 behaviour; with the skill 16/16, without it 0/16. Results: [evals/RESULTS.md](evals/RESULTS.md).
- Every number in `SKILL.md` and these READMEs is checked against the data by `tools/check_numbers.py`.

## Limits

- Measured against Mosaic Pro up to 1.0.13. Features that live only in the 1.0.13 editor (new style-variable types, List classes, pageLoad delay and others) are not measured yet and are not written by the tools.
- Grid child placement properties emit nothing when written headlessly; some interaction shapes are still unmeasured.
- The browser verifiers need Playwright and a site you can write to; they are not part of the offline self-test.
- Open questions: [data/pending.csv](data/pending.csv). The long guide (failure modes, token costs, the Elementor converter, the worked example): [docs/guide.md](docs/guide.md).

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
