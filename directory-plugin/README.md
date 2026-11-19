<h1 align="center">Mosaic Headless</h1>

<h3 align="center">Mosaic Pro 無編輯器建站工具（官方目錄精簡版）</h3>

<p align="center">
  <strong>Measured node types · Style keys that really compile · What goes inside what</strong>
</p>

> This is an unofficial community project. It is not made by, endorsed by, or affiliated with Nextend, the maker of Mosaic Pro. Mosaic Pro is licensed third-party software and is not included here.

This is the **directory edition** of [mosaic-headless](https://github.com/Moksa1123/mosaic-headless): the same measured Mosaic data and reference guides, packaged as reference files only so it fits the Claude plugin directory. It contains no scripts.

## What it does

| Area | What you get |
|---|---|
| Node types | 134 node types, each with the outcome measured when it was committed alone on a live site; 27 are marked unsafe |
| Properties and styles | 120 node properties, 101 style properties and 60 style states, with the value shapes that compile |
| Placement | what each type accepts as children, and what composite types need inside them |
| Design system | 157 variants, 76 dynamic variables, 16 interaction triggers, conditions |
| Chinese terms | designer wording mapped to Mosaic's names (`內距` → padding) |
| Guides | data model, write protocol, failure modes, styling, responsive, dialogs, interactions, upgrades |

## When to use

| Use it for | Use something else for |
|---|---|
| Planning or reviewing Mosaic Pro pages, templates and components; "what is it called / is it safe" | Elementor or block-editor pages |
| Explaining why a Mosaic page renders wrong | WordPress health checks, plugin updates |

## Install

```
/plugin install mosaic-headless
```

The full edition adds the page builder, the delivered-page verifiers and the theme tools:

```bash
npx mosaic-headless@1.38.3 claude-code --global
```

## Quick start

- "Can I put an accordion-content directly inside a div in Mosaic?"
- "Which Mosaic style key sets the border radius, and what value shape does it take?"
- "Add a popover tour with three steps that advances when each step closes: which nodes and triggers?"

## What it runs and connects to

- **Nothing.** This edition contains Markdown, JSON and an icon only: no scripts, no hooks, no MCP servers, no network access.
- Claude reads the JSON tables and guides in `skills/mosaic-headless/` to answer.
- It asks for no credentials and reads nothing outside its own folder.
- No data is sent to the author or anyone else.

## How it's verified

The tables come from the Mosaic Pro 1.0.13 plugin source and from writing each item to a live install and reading the delivered page back. The full edition's self-test, evals and verification record are in the [source repository](https://github.com/Moksa1123/mosaic-headless). This folder is generated from that repository's files by `scripts/build_directory.py`, which also refuses to build if the output would mention server logins or credentials.

## Limits

- Lookups only: committing pages, checking delivered pages and moving themes need the full edition.
- Features that live only in the Mosaic 1.0.13 editor are not measured yet; open questions are in `data/pending.json`.

## License & author

MIT License. Made by Moksa.
