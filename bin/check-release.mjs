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
  "data/rwd-verification.csv": 731,
  "data/browser-verification.csv": 3988,
  "data/style-state-verification.csv": 52,
  "data/interaction-verification.csv": 7,
  "data/data-class-hierarchy.csv": 121,
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

// The browser pass has the same obligation, under a different word: a declaration it
// cannot soundly compare must say so rather than be counted as agreement.
const browser = read("data/browser-verification.csv");
if (!browser.includes("not-comparable"))
  fail("browser-verification.csv has no not-comparable rows - a computed-value check "
     + "that claims to compare everything is comparing things it cannot");
if (browser.includes("OVERRIDDEN"))
  fail("browser-verification.csv still contains OVERRIDDEN rows - the shipped example "
     + "must render what it declares");

// The design audit ships even when it is empty, and empty has to mean "ran and found
// nothing" rather than "was never run", so the header alone is the proof.
// The intro table is two tables in one file - the checks and the timeline readings -
// so a row count says nothing useful about it. What matters is that every check
// passed, because a shipped example whose entrance animation never lifts is a blank
// page for every visitor.
const intro = read("data/intro-verification.csv");
if (!intro.startsWith("check,result,detail"))
  fail("data/intro-verification.csv is not the table verify_intro.py writes");
for (const need of ["PLAYS", "ENDS", "NO_TRAP", "CLEARS", "DEGRADES", "AMBIENT"])
  if (!new RegExp(`^${need},PASS`, "m").test(intro))
    fail(`intro-verification.csv: ${need} did not pass`);
if (/,FAIL,/.test(intro)) fail("data/intro-verification.csv carries a failed check");

// The loop table is the same shape and the same obligation: a decoration that runs
// forever is the easiest thing in this repo to ship broken, because it looks fine in
// a screenshot whether or not it ever moves again.
const loop = read("data/loop-verification.csv");
if (!loop.startsWith("check,result,detail"))
  fail("data/loop-verification.csv is not the table verify_loop.py writes");
for (const need of ["RUNS", "SCRUBBABLE", "REDUCED"])
  if (!new RegExp(`^${need},PASS`, "m").test(loop))
    fail(`loop-verification.csv: ${need} did not pass`);
if (!/^CLEAR@\d+,PASS/m.test(loop))
  fail("loop-verification.csv has no CLEAR@<width> row - occlusion was never checked");
if (/,FAIL,/.test(loop)) fail("data/loop-verification.csv carries a failed check");

// The accordion probe exists to correct a row in node-verification.csv, so it has
// to keep passing or the correction silently becomes another wrong claim.
const acc = read("data/accordion-verification.csv");
if (!acc.startsWith("step,result,detail"))
  fail("data/accordion-verification.csv is not the table probe_accordion.py writes");
if (/,FAIL,/.test(acc)) fail("data/accordion-verification.csv carries a failed check");

// The ZIP round trip: a table of PASS rows that must stay PASS, because the day the
// native import starts dropping something other than orphans is the day this skill
// starts recommending a tool that loses pages.
const zip = read("data/theme-zip-verification.csv");
if (!zip.startsWith("check,result,detail"))
  fail("data/theme-zip-verification.csv is not the table theme_zip_compare.php writes");
for (const need of ["nodes", "tree shape", "live untouched"])
  if (!new RegExp(`^"?${need}"?,PASS`, "m").test(zip))
    fail(`theme-zip-verification.csv: ${need} did not pass`);
if (/,FAIL,/.test(zip)) fail("data/theme-zip-verification.csv carries a failed check");

// The READMEs quote the same counts as SKILL.md, in four languages, and they are
// what a visitor reads first. A count that moved in the CSV and not in a README was
// a public claim that stayed wrong for a week; so every README must carry the live
// rwd and browser counts, and must not carry the previous ones.
{
  const fmt = (n) => n.toLocaleString("en-US");
  const want = [rows("data/rwd-verification.csv"), rows("data/browser-verification.csv")];
  for (const readme of ["README.md", "README.zh-TW.md", "README.ja.md", "README.ko.md"]) {
    const text = read(readme);
    for (const n of want)
      if (!text.includes(fmt(n)) && !text.includes(String(n)))
        fail(`${readme} does not quote ${fmt(n)} - it is quoting a stale count`);
    if (/0 findings|指摘 0 件|지적 0건|0 項發現/.test(text))
      fail(`${readme} still claims a design audit with 0 findings`);
  }
}

// The conversion table is the one that can rot without anyone noticing: the
// converter keeps reporting "N elements converted" whatever it produces, and only
// this table says whether the page survived.
const conv = read("data/conversion-verification.csv");
if (!conv.startsWith("check,result,detail"))
  fail("data/conversion-verification.csv is not the table verify_conversion.py writes");
for (const need of ["TEXT", "IMAGES", "LINKS", "HEADINGS", "RWD", "COMPUTED", "FIDELITY"])
  if (!new RegExp(`^${need},PASS`, "m").test(conv))
    fail(`conversion-verification.csv: ${need} did not pass`);
if (/,FAIL,/.test(conv)) fail("data/conversion-verification.csv carries a failed check");
if (/^IMAGES,PASS,"?0 of 0/m.test(conv))
  fail("conversion-verification.csv: IMAGES passed vacuously on a page with no images");

const audit = read("data/design-audit.csv");
if (!audit.startsWith("url,breakpoints,check,level"))
  fail("data/design-audit.csv is not the audit table verify_browser.py writes");
if (audit.includes(",error,"))
  fail("data/design-audit.csv carries unresolved design errors");

// Stronger than "no errors": every finding must be either FIXED or ACKNOWLEDGED in
// writing. A warning that nobody has ruled on is the state this gate exists to
// prevent - it is how a list of findings turns into a list nobody reads.
if (audit.includes(",warn,"))
  fail("data/design-audit.csv carries warnings that are neither fixed nor "
     + "acknowledged in data/design-audit-acknowledged.csv");
const ackFile = "data/design-audit-acknowledged.csv";
if (!fs.existsSync(path.join(ROOT, ackFile))) fail(`${ackFile} missing`);
else {
  const ack = read(ackFile);
  if (!ack.startsWith("check,node_prefix,reason"))
    fail(`${ackFile} is not the acknowledgement table verify_browser.py reads`);
  // an acknowledgement without a reason is a suppression wearing a better name
  for (const line of ack.trim().split("\n").slice(1))
    if (line.length < 60)
      fail(`${ackFile}: an acknowledgement has no substantive reason: `
         + line.slice(0, 60));
}

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
    // npm 11 returns an array of packed packages; npm 12 returns an object keyed
    // by package name. Reading only the array shape against npm 12 yields zero
    // files, and a leak check over zero files passes - which is the blind spot
    // scored as a success that this whole file exists to prevent. The
    // `files.length === 0` assertion below is the backstop that caught it.
    const parsed = JSON.parse(packed);
    const packs = Array.isArray(parsed) ? parsed : Object.values(parsed);
    files = (packs[0]?.files || []).map((f) => f.path.split("\\").join("/"));
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
