#!/usr/bin/env node
/**
 * Write package.json's version into every other place that carries one.
 *
 *   node bin/sync-version.mjs
 *
 * Runs from the `version` npm lifecycle script, after npm has bumped package.json
 * and before it makes the commit and the tag - so the tagged commit already has all
 * three versions agreeing, and `npm version patch` is the only command anyone has to
 * remember.
 *
 * Targets:
 *   SKILL.md                              frontmatter `version:`
 *   assets/templates/platforms/*.json     frontmatter.version, where present
 *
 * check-release.mjs asserts afterwards that this worked, so a silent miss here
 * cannot reach npm.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const pkg = JSON.parse(fs.readFileSync(path.join(ROOT, "package.json"), "utf8"));
const v = pkg.version;
const touched = [];

// SKILL.md - only inside the frontmatter block, never in the prose below it
const skillPath = path.join(ROOT, "SKILL.md");
let skill = fs.readFileSync(skillPath, "utf8");
const end = skill.indexOf("\n---", 4);
if (end === -1) {
  console.error("SKILL.md has no frontmatter block");
  process.exit(1);
}
const head = skill.slice(0, end);
const rest = skill.slice(end);
// "already correct" and "line missing" are different answers, and conflating them
// made this exit 1 on a release where the version happened to match already.
const VERSION_LINE = /^version:\s*"?[^"\n]*"?\s*$/m;
if (!VERSION_LINE.test(head)) {
  console.error("SKILL.md frontmatter has no version: line to update");
  process.exit(1);
}
const next = head.replace(VERSION_LINE, `version: "${v}"`);
if (next !== head) {
  fs.writeFileSync(skillPath, next + rest);
  touched.push("SKILL.md");
}

// platform templates
const platDir = path.join(ROOT, "assets", "templates", "platforms");
for (const f of fs.readdirSync(platDir).filter((x) => x.endsWith(".json"))) {
  const p = path.join(platDir, f);
  const cfg = JSON.parse(fs.readFileSync(p, "utf8"));
  if (cfg.frontmatter && "version" in cfg.frontmatter && cfg.frontmatter.version !== v) {
    cfg.frontmatter.version = v;
    fs.writeFileSync(p, JSON.stringify(cfg, null, 2) + "\n");
    touched.push(`assets/templates/platforms/${f}`);
  }
}

console.log(`synced v${v} into ${touched.length} file(s): ${touched.join(", ") || "none"}`);
