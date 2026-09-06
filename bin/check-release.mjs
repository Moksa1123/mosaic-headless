#!/usr/bin/env node
/**
 * Refuse to publish a package that does not hold together.
 *
 *   node bin/check-release.mjs
 *
 * Runs as `preversion` and again as `prepublishOnly`, so a release cannot be cut or
 * pushed while any of this is false. Exits non-zero with the reason.
 *
 * The version number exists in three places - package.json, the SKILL.md
 * frontmatter an agent reads, and the frontmatter each platform template writes on
 * install. Nothing keeps them together on its own, and a skill that reports a
 * version it is not is worse than one that reports none. `npm version` runs
 * sync-version.mjs to write all three; this asserts it worked.
 *
 * It also checks that every path in package.json `files` exists, that the data files
 * the skill's own claims rest on are present and non-trivial, and that the
 * verification CSVs still say what SKILL.md says they say. The last one is the point:
 * the headline numbers in the documentation are counted from the data at release
 * time rather than trusted.
 */
import { execSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const read = (p) => fs.readFileSync(path.join(ROOT, p), "utf8");
const problems = [];
const fail = (m) => problems.push(m);

// ---------- versions agree --------------------------------------------------

const pkg = JSON.parse(read("package.json"));
const want = pkg.version;

const skill = read("SKILL.md");
const fmVersion = /^version:\s*"?([^"\n]+)"?\s*$/m.exec(skill.split("---")[1] || "");
if (!fmVersion) fail("SKILL.md frontmatter has no version:");
else if (fmVersion[1].trim() !== want)
  fail(`SKILL.md version ${fmVersion[1].trim()} != package.json ${want}`);

const platDir = path.join(ROOT, "assets", "templates", "platforms");
for (const f of fs.readdirSync(platDir).filter((x) => x.endsWith(".json"))) {
  const cfg = JSON.parse(fs.readFileSync(path.join(platDir, f), "utf8"));
  const v = cfg.frontmatter?.version;
  if (v !== undefined && v !== want) fail(`${f} frontmatter version ${v} != ${want}`);
  if (JSON.stringify(cfg).includes("gutenberg-headless"))
    fail(`${f} still names another skill`);
}

// ---------- everything the package claims to ship actually exists -----------

// `files` entries are globs, not paths - a directory shipped whole is the mistake
// this list exists to avoid, so the check has to understand `data/*.csv`.
for (const entry of pkg.files) {
  const star = entry.indexOf("*");
  if (star === -1) {
    if (!fs.existsSync(path.join(ROOT, entry)))
      fail(`package.json files lists ${entry}, which does not exist`);
    continue;
  }
  const dir = entry.slice(0, entry.lastIndexOf("/"));
  const pattern = entry.slice(entry.lastIndexOf("/") + 1);
  const quote = (x) => x.replace(/[-.+?^${}()|[\]\\]/g, "\\$&");
  const re = new RegExp("^" + pattern.split("*").map(quote).join(".*") + "$");
  const abs = path.join(ROOT, dir);
  if (!fs.existsSync(abs) || !fs.readdirSync(abs).some((f) => re.test(f)))
    fail(`package.json files lists ${entry}, which matches nothing`);
}
if (!fs.existsSync(path.join(ROOT, pkg.bin["mosaic-headless"])))
  fail(`bin points at ${pkg.bin["mosaic-headless"]}, which does not exist`);

// ---------- the numbers in the docs are counted, not trusted ----------------

const rows = (p) => read(p).trim().split("\n").length - 1;   // minus the header
const counts = {
  "data/node-verification.csv": 122,
  "data/style-verification.csv": 98,
  "data/node-property-verification.csv": 181,
  "data/rwd-verification.csv": 576,
};
for (const [file, expected] of Object.entries(counts)) {
  if (!fs.existsSync(path.join(ROOT, file))) { fail(`${file} missing`); continue; }
  const n = rows(file);
  if (n !== expected) fail(`${file} has ${n} rows, SKILL.md claims ${expected}`);
  if (!skill.includes(String(expected)))
    fail(`SKILL.md never mentions ${expected}, but ${file} has that many rows`);
}

// a sweep whose own blind spots were folded into a pass rate is the failure this
// skill argues against, so the labels have to survive into the shipped data
const style = read("data/style-verification.csv");
if (!style.includes("SKIPPED")) fail("style-verification.csv has no SKIPPED rows - "
  + "blind spots should be labelled, not dropped");

// ---------- nothing private ships -------------------------------------------

// npm's `files` allowlist OVERRIDES .gitignore: naming a directory there ships
// everything inside it, ignored or not. Listing `sites/` once put a real client's
// page generator and content into the tarball - gitignored, and published anyway.
// So the tarball is inspected rather than the intent trusted.
let packed = "";
try {
  // execSync with one fixed command string: on Windows `npm` is npm.cmd, which
  // execFileSync will not resolve, and passing an args array with shell:true is
  // deprecated. Nothing here is interpolated, so there is nothing to escape.
  packed = execSync("npm pack --dry-run --json",
                    { cwd: ROOT, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] });
} catch {
  fail("could not run `npm pack --dry-run` to inspect the tarball");
}
if (packed) {
  let files = [];
  try {
    files = (JSON.parse(packed)[0]?.files || []).map((f) => f.path.split("\\").join("/"));
  } catch { fail("could not parse `npm pack --json` output"); }

  const forbidden = [
    [/^sites\/_zidanna/, "a real client's page generator"],
    [/^sites\/zidanna\./, "a real client's content"],
    [/^data\/raw\//, "raw capture dumps"],
    [/__pycache__/, "python build artefacts"],
    [/^shots\//, "screenshots"],
    [/\.env|secret|credential/i, "something that looks like a secret"],
  ];
  for (const [re, what] of forbidden) {
    const hit = files.filter((f) => re.test(f));
    if (hit.length) fail(`tarball would ship ${what}: ${hit.slice(0, 3).join(", ")}`);
  }
  if (files.length === 0) fail("npm pack reported no files");
  console.log(`tarball inspected: ${files.length} files, nothing forbidden`);
}

// ---------- report ----------------------------------------------------------

if (problems.length) {
  console.error(`release check failed (${problems.length}):`);
  for (const p of problems) console.error("  - " + p);
  process.exit(1);
}
console.log(`release check passed: v${want}, ${pkg.files.length} shipped paths, `
  + `${Object.keys(counts).length} verification tables counted`);
