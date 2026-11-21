#!/usr/bin/env python3
"""test_mosaic.py - offline self-test for the skill (skill SOP item 8).

    python tools/test_mosaic.py          # exit 1 on any failure

No network, no site, no third-party packages. Covers:
  - mo.py: the front door answers, exits 1 on unsafe / unknown, Chinese terms resolve
  - data/terms-zh.csv: every row sourced, every English target exists in the data
  - build_page: a spec flattens to the editor's shape and unsafe input is refused
  - build_page / build_site: the public signatures em925 imports are unchanged
  - SKILL.md: size, fixed headings, every number claimed (check_numbers), links resolve
  - references/data-files.md: every row count matches its CSV
  - data/pending.csv exists with its columns

The browser verifiers (tools/verify_*.py) need a live site and playwright and are
not run here; see SKILL.md ## Verify.
"""
from __future__ import annotations

import csv
import inspect
import json
import os
import re
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, HERE)

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")


def mo(*args):
    r = subprocess.run([sys.executable, os.path.join(HERE, "mo.py"), *args],
                       capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stdout + r.stderr


def rows(name):
    with open(os.path.join(DATA, name), encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


class MoQueries(unittest.TestCase):
    def test_stats(self):
        code, out = mo("--json", "stats")
        self.assertEqual(code, 0, out)
        s = json.loads(out)
        self.assertEqual(s["node_types"], len(rows("node-types.csv")))
        self.assertEqual(s["node_property_declarations"], len(rows("node-properties.csv")))
        self.assertEqual(s["node_properties"], len(rows("node-property-verification.csv")))
        self.assertIn("accordion-content", s["unsafe_types"])

    def test_stats_explains_declared_vs_probed(self):
        code, out = mo("stats")
        self.assertEqual(code, 0)
        self.assertIn("declared once per owning data class", out)

    def test_type_leads_with_verdict(self):
        code, out = mo("--json", "type", "accordion-content")
        self.assertEqual(code, 0, out)
        rec = json.loads(out)
        self.assertEqual(rec["outcome"], "BROKE_PAGE")
        self.assertFalse(rec["safe_to_commit"])

    def test_check_exit_codes(self):
        self.assertEqual(mo("check", "div", "text", "button")[0], 0)
        self.assertEqual(mo("check", "accordion-content")[0], 1)
        self.assertNotEqual(mo("check", "no-such-type")[0], 0)

    def test_select_split_1012(self):
        code, out = mo("--json", "placement", "select")
        self.assertEqual(code, 0, out)
        self.assertNotIn("select-input", {r["type"] for r in rows("node-types.csv")})

    def test_css_reverse_lookup(self):
        code, out = mo("css", "border-radius")
        self.assertEqual(code, 0)
        self.assertIn("borderRadius", out)

    def test_css_not_a_style_key(self):
        code, out = mo("css", "clip-path")
        self.assertEqual(code, 1)
        self.assertIn("not a Mosaic style key", out)
        self.assertIn("customDeclarations", out)
        code, out = mo("css", "border-radus")
        self.assertIn("did you mean: border-radius", out)
        self.assertEqual(mo("css", "object-fit")[0], 0)       # it does have a key: objectFitStyle

    def test_params(self):
        code, out = mo("--json", "params", "text")
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads(out)["type"], "text")


class ChineseTerms(unittest.TestCase):
    def test_css_padding_in_chinese(self):
        code, out = mo("css", "內距")
        self.assertEqual(code, 0, out)
        for p in ("paddingTop", "paddingRight", "paddingBottom", "paddingLeft"):
            self.assertIn(p, out)

    def test_shipped_and_designer_terms_agree(self):
        self.assertEqual(mo("css", "內距")[1], mo("css", "邊框間距")[1])
        self.assertEqual(mo("css", "外距")[1], mo("css", "邊界")[1])

    def test_state_hover(self):
        code, out = mo("states", "--grep", "懸停")
        self.assertEqual(code, 0)
        self.assertIn("hover", out)

    def test_type_by_chinese_name(self):
        code, out = mo("--json", "type", "摺疊面板")
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads(out)["type"], "accordion")

    def test_ambiguous_type_refused(self):
        code, out = mo("type", "彈窗")
        self.assertNotEqual(code, 0)
        self.assertIn("modal", out)

    def test_unmapped_word_points_at_pending(self):
        code, out = mo("css", "完全沒有這個詞")
        self.assertEqual(code, 1)
        self.assertIn("pending.csv", out)

    def test_wrong_kind_says_so(self):
        code, out = mo("css", "按鈕")
        self.assertEqual(code, 1)
        self.assertIn("type term", out)

    def test_terms_command(self):
        code, out = mo("--json", "terms", "斷點")
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads(out)[0]["en"], "breakpoint")


class TermsTable(unittest.TestCase):
    TRUST = {"measured", "documented", "inferred", "house-style"}

    @classmethod
    def setUpClass(cls):
        cls.terms = rows("terms-zh.csv")
        cls.types = {r["type"] for r in rows("node-types.csv")}
        cls.states = [r["state"] for r in rows("style-states.csv")]
        cls.css = [(r["css_property"] + " " + r["property"]).lower()
                   for r in rows("style-verification.csv")]

    def test_columns_and_provenance(self):
        for r in self.terms:
            self.assertEqual(set(r), {"zh", "en", "kind", "note", "source", "trust"}, r)
            self.assertTrue(r["zh"] and r["en"] and r["source"], r)
            self.assertIn(r["trust"], self.TRUST, r)
            self.assertIn(r["kind"], {"css", "type", "state", "concept"}, r)

    def test_no_duplicate_words(self):
        zh = [r["zh"] for r in self.terms]
        self.assertEqual(len(zh), len(set(zh)))

    def test_every_target_exists(self):
        for r in self.terms:
            for en in r["en"].split("|"):
                if r["kind"] == "type":
                    self.assertIn(en, self.types, r["zh"])
                elif r["kind"] == "state":
                    self.assertTrue(any(en in s for s in self.states), r["zh"])
                elif r["kind"] == "css":
                    self.assertTrue(any(en in c for c in self.css), r["zh"])

    def test_designer_glossary_present(self):
        by = {r["zh"]: r for r in self.terms}
        # the 2026-11-05 designer glossary, shipped by Mosaic from 1.0.13
        for zh, en in (("內距", "padding"), ("外距", "margin"), ("懸停", "hover"), ("斷點", "breakpoint")):
            self.assertEqual(by[zh]["en"], en)
            self.assertEqual(by[zh]["trust"], "documented")
            self.assertIn("1.0.13", by[zh]["source"])
        # the wording it replaced still resolves, for sites on 1.0.12 and earlier
        for zh in ("邊框間距", "邊界", "游標暫留", "中斷點"):
            self.assertIn("replaced in 1.0.13", by[zh]["source"])


class BuildPageOffline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import build_page
        cls.bp = build_page
        cls.surface = build_page.Surface()
        build_page.VAR_IDS["--ink"] = "11111111-1111-1111-1111-111111111111"

    def flat(self, tree):
        return self.bp.flatten(self.bp.refresh_node_ids(tree), "BODY", "MASTER",
                               self.surface, False, parent_type="body")

    def skeleton_tree(self):
        code, out = mo("skeleton")
        self.assertEqual(code, 0)
        return json.loads(out)["pages"][0]["tree"]

    def test_skeleton_flattens(self):
        recs = self.flat(self.skeleton_tree())
        self.assertEqual([r["type"] for r in recs], ["div", "text", "wysiwyg-text"])
        for r in recs:
            self.assertEqual(r["documentType"], "master")
            self.assertEqual(r["documentID"], "MASTER")
            self.assertIsInstance(r["ordering"], str)       # fractional index, never a number
        self.assertEqual(recs[0]["parentID"], "BODY")
        self.assertEqual(recs[1]["parentID"], recs[0]["ID"])
        style = recs[1]["data"]["style"]["states"]["&"]
        self.assertEqual(style["_"]["color"], {"var": "11111111-1111-1111-1111-111111111111"})
        self.assertIn("_m", style)

    def test_button_text_wrapped_like_the_editor(self):
        recs = self.flat({"type": "div", "children": [
            {"type": "button", "data": {"url": {"v": "/contact/"}}, "text": "Go"}]})
        types = [r["type"] for r in recs]
        self.assertEqual(types, ["div", "button", "text", "wysiwyg-text"])
        self.assertEqual(recs[2]["data"]["style"]["variant"], self.bp.INHERITED_TEXT_VARIANT)
        self.assertEqual(recs[3]["parentID"], recs[2]["ID"])

    def test_sibling_ordering(self):
        recs = self.flat({"type": "div", "children": [{"type": "div"}, {"type": "div"}, {"type": "div"}]})
        self.assertEqual([r["ordering"] for r in recs[1:]], ["a0", "a1", "a2"])

    def test_pinned_ids_are_refreshed(self):
        tree = {"type": "div", "nodeID": "pin-a", "children": [{"type": "div", "nodeID": "pin-b"}]}
        a = self.flat(json.loads(json.dumps(tree)))
        b = self.flat(json.loads(json.dumps(tree)))
        self.assertNotEqual(a[0]["ID"], "pin-a")
        self.assertNotEqual(a[0]["ID"], b[0]["ID"])

    def assertRefused(self, tree, needle):
        with self.assertRaises(SystemExit) as cm:
            self.flat(tree)
        self.assertIn(needle, str(cm.exception))

    def test_refuses_unsafe_placement(self):
        self.assertRefused({"type": "div", "children": [{"type": "accordion-content"}]}, "BROKE_PAGE")

    def test_refuses_unknown_type(self):
        self.assertRefused({"type": "nosuch"}, "unknown node type")

    def test_refuses_unknown_style_key(self):
        self.assertRefused({"type": "div", "style": {"&": {"_": {"noSuchProp": "1"}}}}, "not a supported style property")

    def test_refuses_out_of_enum(self):
        self.assertRefused({"type": "div", "style": {"&": {"_": {"whiteSpace": "pre-line"}}}}, "pre-line")

    def test_refuses_media_without_space(self):
        self.assertRefused({"type": "code", "data": {"content": "@media(max-width:1px){}"}}, "@media(")

    def test_refuses_tags_in_text_run(self):
        self.assertRefused({"type": "text", "text": "a<b>c</b>"}, "<b>")


class PublicInterface(unittest.TestCase):
    """em925's deploy tool imports build_page and build_site from the global
    install. Their names and parameters are a contract: change one and this fails."""

    EXPECTED = {
        "build_page": {
            "build": "(client, cfg, spec, force)",
            "flatten": "(node, parent_id, master_id, surface, force, ordering='a0', parent_type=None, out=None, ancestors=())",
            "refresh_node_ids": "(tree)",
            "wrap_text_runs": "(node_type, children)",
            "to_style": "(spec_style)",
            "expand_shorthands": "(props)",
            "theme_records": "(spec, doc, surface)",
            "create_master": "(client, name)",
            "bind_template": "(client, cfg, master_id, page_id)",
            "ordering_for": "(index)",
            "load_csv": "(name)",
        },
        "build_site": {
            "main": "()",
            "build_shell": "(client, cfg, site, surface)",
            "fill_shell": "(client, cfg, site, surface, master_id, header_id, footer_id, comps)",
            "ensure_components": "(client, cfg, site, surface)",
            "apply_overrides": "(client, instance, key, uses, comps, envelope='templateDocumentInstance')",
            "bind_page": "(client, cfg, master_id, slug, post_id)",
            "build_page_document": "(client, cfg, master_id, template_id, tree, surface)",
            "resolve_components": "(node, comps)",
            "cache_check": "(url, _fresh_bytes=None)",
            "commit": "(client, instance, doc, payload, what)",
        },
    }

    def test_signatures_unchanged(self):
        import importlib
        for mod, funcs in self.EXPECTED.items():
            m = importlib.import_module(mod)
            for name, sig in funcs.items():
                self.assertTrue(hasattr(m, name), "%s.%s is gone" % (mod, name))
                self.assertEqual(str(inspect.signature(getattr(m, name))), sig, "%s.%s" % (mod, name))
        # every name em925's deploy tool imports (em925_update.py, fill_templates.py,
        # component_categories.py), as em925-總機 listed them on 2026-11-16
        import build_page
        import build_site
        for name in ("Surface", "flatten", "refresh_node_ids", "theme_records",
                     "COMPONENT_USES", "unwrap"):
            self.assertTrue(hasattr(build_page, name), "build_page." + name)
        for name in ("commit", "ensure_components", "resolve_components", "apply_overrides",
                     "COMPONENT_NAMESPACE", "build_page_document"):
            self.assertTrue(hasattr(build_site, name), "build_site." + name)


class SkillDoc(unittest.TestCase):
    HEADINGS = ["## Sources", "## Usage", "## Routing", "## Tasks", "## Verify", "## Maintenance"]

    def test_size(self):
        self.assertLessEqual(os.path.getsize(os.path.join(ROOT, "SKILL.md")), 20 * 1024)

    def test_headings_in_order(self):
        text = read("SKILL.md")
        pos = [text.find("\n" + h + "\n") for h in self.HEADINGS]
        self.assertTrue(all(p > 0 for p in pos), pos)
        self.assertEqual(pos, sorted(pos))

    def test_iron_rule_heads_routing(self):
        text = read("SKILL.md")
        routing = text[text.index("## Routing"):]
        first = routing.split("\n\n")[1]
        self.assertIn("never answer from memory", first)
        self.assertIn("data/pending.csv", first)

    def test_frontmatter(self):
        fm = read("SKILL.md").split("---", 2)[1]
        self.assertRegex(fm, r"(?m)^user-invocable: true$")
        self.assertRegex(fm, r"(?m)^description: \|$")       # install.mjs needs the block form
        self.assertRegex(fm, r"(?m)^  version: ")             # under metadata (check-release)

    def test_numbers_claimed(self):
        import check_numbers
        problems, _ = check_numbers.check()
        self.assertEqual(problems, [])

    def test_readme_numbers_claimed(self):
        import check_numbers
        from pathlib import Path
        facts = check_numbers._readme_facts()
        for name in check_numbers.READMES:
            problems, _ = check_numbers.check(Path(ROOT) / name, rules=check_numbers.README_RULES,
                                              facts=facts, allow_unused=True)
            self.assertEqual(problems, [], name)
            text = read(name)
            # every README states the headline facts, not just the ones it happens to mention
            for key in ("node_types", "rwd", "browser", "tests", "eval_with", "eval_without"):
                self.assertIn(facts[key], text, "%s lacks %s" % (name, key))

    def test_readme_sections(self):
        # README style (總機/README風格.md): the same 10 sections, in order, in every language
        heads = {
            "README.md": ["What it does", "When to use", "Install", "Quick start", "Trigger phrases",
                          "What it runs and connects to", "How it's verified", "Limits",
                          "Repo layout", "License & author"],
            "README.zh-TW.md": ["功能", "適用情境", "安裝", "快速開始", "觸發詞", "會執行與連線的內容",
                                "驗證方式", "限制", "目錄結構", "授權與作者"],
        }
        for name in ("README.md", "README.zh-TW.md", "README.ja.md", "README.ko.md"):
            text = read(name)
            found = re.findall(r"^## (.+)$", text, re.M)
            self.assertEqual(len(found), 10, name)
            if name in heads:
                self.assertEqual(found, heads[name], name)
            self.assertLessEqual(text.count("\n"), 250, name)
            self.assertIn("Nextend", text, name)
            # the visual template (總機/README範本-taiwan原版.md): centred h1 + h3, three badge
            # rows, and the tables restored from the pre-v1.38 README
            self.assertTrue(text.startswith('<h1 align="center">'), name)
            self.assertIn('<h3 align="center">', text, name)
            self.assertGreaterEqual(text.count("img.shields.io"), 12, name)
            for badge in ("/badge/node_types-", "/badge/style_properties-", "/badge/self--tests-",
                          "/npm/v/mosaic-headless", "/npm/dt/mosaic-headless"):
                self.assertIn(badge, text, name)
            tables = len(re.findall(r"^\|[-:| ]+\|$", text, re.M))
            self.assertGreaterEqual(tables, 6, "%s has %d tables" % (name, tables))
            for row in ("| Claude.ai |", "`data/rwd-verification.csv`", "`css grid-column`",
                        "`theme_zip.py`"):
                self.assertIn(row, text, name)

    def test_links_resolve(self):
        text = read("SKILL.md")
        for target in re.findall(r"\]\(([^)#]+)\)", text):
            if target.startswith("http"):
                continue
            self.assertTrue(os.path.exists(os.path.join(ROOT, target)), target)

    def test_referenced_tools_exist(self):
        text = read("SKILL.md")
        # the override check is documented as read only: keep it that way
        sql = read("tools/override_health.sql")
        body = "\n".join(l for l in sql.splitlines() if not l.lstrip().startswith("--"))
        self.assertIsNone(re.search(r"\b(DELETE|UPDATE|INSERT|REPLACE|DROP|ALTER|TRUNCATE)\b", body, re.I))
        for name in set(re.findall(r"\b([a-z_]+\.(?:py|php|sql))\b", text)):
            hits = [os.path.join(d, name) for d in ("tools", "sites", "evals")
                    if os.path.exists(os.path.join(ROOT, d, name))]
            self.assertTrue(hits, name)


class SyncNodesPlan(unittest.TestCase):
    """sync_nodes.py's matching, offline: a live document is simulated as the same spec
    flattened again (fresh node ids, the way a commit stores it)."""

    @classmethod
    def setUpClass(cls):
        import build_page
        import sync_nodes
        cls.bp, cls.sn = build_page, sync_nodes
        cls.surface = build_page.Surface()

    def tree(self, title="Hello", extra=False):
        kids = [{"type": "text", "data": {"tagName": "h1", "attrID": "t-title"}, "text": title},
                {"type": "button", "data": {"url": {"v": "/contact/"}, "attrID": "t-cta"}, "text": "Go"}]
        if extra:
            kids.append({"type": "text", "data": {"attrID": "t-new"}, "text": "New"})
        return {"type": "div", "data": {"attrID": "t-root"}, "children": kids}

    def flat(self, tree, top):
        return self.bp.flatten(self.bp.refresh_node_ids(tree), top, "DOC", self.surface, False,
                               parent_type="template-internal")

    def test_identical_tree_needs_nothing(self):
        same, struct, updates, _ = self.sn.plan(self.flat(self.tree(), "S"), "S", self.flat(self.tree(), "L"), "L")
        self.assertTrue(same)
        self.assertEqual((struct, updates), ([], []))

    def test_text_edit_is_one_update(self):
        same, struct, updates, _ = self.sn.plan(self.flat(self.tree("Changed"), "S"), "S",
                                                self.flat(self.tree(), "L"), "L")
        self.assertTrue(same)
        self.assertEqual(len(updates), 1)
        live, merged, changed = updates[0]
        self.assertEqual((live["type"], changed, merged["text"]), ("wysiwyg-text", ["text"], "Changed"))

    def test_added_node_is_structural(self):
        same, struct, updates, _ = self.sn.plan(self.flat(self.tree(extra=True), "S"), "S",
                                                self.flat(self.tree(), "L"), "L")
        self.assertFalse(same)
        self.assertTrue(any("@t-new" in s for s in struct))

    # what a live 1.0.13 site did to an unchanged spec (2026-11-21): random list-item
    # uuids on every build, re-spaced CSS, a rewritten svg, a heal-inserted child
    SVG = '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M0 0h24v24H0z"/></svg>'

    def rich_tree(self, title="Hello", body="Body"):
        return {"type": "div", "data": {"attrID": "r-root"},
                "style": {"&": {"_": {"shadow": {"x": "0px", "y": "4px", "color": "rgba(0,0,0,.2)"},
                                       "transitionAll": "200ms ease", "move": {"translateY": "-8px"},
                                       "customDeclarations": "outline:0;font-feature-settings:'palt' 1,'kern' 1"}}},
                "children": [
                    {"type": "icon", "data": {"attrID": "r-icon", "svg": self.SVG}},
                    {"type": "text", "data": {"tagName": "h2", "attrID": "r-title"}, "text": title},
                    {"type": "accordion", "data": {"attrID": "r-acc"}, "children": [
                        {"type": "accordion-item", "data": {"attrID": "r-item"}, "children": [
                            {"type": "accordion-title", "data": {"attrID": "r-q"}, "text": "Q"},
                            {"type": "accordion-content", "data": {"attrID": "r-a"}}]}]},
                    {"type": "text", "data": {"attrID": "r-body"}, "text": body},
                    {"type": "button", "nodeID": "pin-target", "data": {"attrID": "r-btn", "url": {"v": "/x/"},
                     "attributes": [{"name": "aria-label", "value": "Open"}]},
                     "style": {"&": {"_": {"backgroundColor": "rgba(0,0,0,0)", "color": "rgb(255,255,255)"}}},
                     "text": "Open"},
                    {"type": "div", "data": {"attrID": "r-opener", "interactions": [
                        {"uuid": "11111111-2222-4333-8444-555555555555", "type": "click",
                         "clickOptions": {"ID": "66666666-7777-4888-9999-000000000000"},
                         "settings": {"target": {"type": "element", "uuid": "pin-target"}}}]}}]}

    def as_stored(self, records):
        """What Mosaic hands back: CSS re-spaced, svg rewritten, default children added."""
        import uuid as _uuid
        out = []
        for r in records:
            r = json.loads(json.dumps(r))
            st = ((r.get("data") or {}).get("style") or {}).get("states") or {}
            for bps in st.values():
                for props in bps.values():
                    if "customDeclarations" in props:
                        props["customDeclarations"] = (props["customDeclarations"]
                                                       .replace(":", ": ").replace(",", ", ")
                                                       .replace(";", ";\n"))
                    for ck in ("backgroundColor", "color"):
                        if isinstance(props.get(ck), str):
                            props[ck] = props[ck].replace(",", ", ")
            d = r.get("data") or {}
            if "attributes" in d:                          # button / menu-link keep none
                d["attributes"] = None
            for it in d.get("interactions") or []:          # stored without these
                it.pop("uuid", None)
                (it.get("clickOptions") or {}).pop("ID", None)
            if r["type"] == "icon":
                r["data"]["svg"] = ('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" '
                                    'fill="none" viewBox="0 0 24 24"><path d="M0 0h24v24H0z"/></svg>')
            out.append(r)
            if r["type"] == "accordion-content":            # heal fills an empty panel
                t = {"ID": str(_uuid.uuid4()), "parentID": r["ID"], "parentType": "node", "type": "text",
                     "ordering": "a0", "status": "publish", "data": {}}
                out += [t, {"ID": str(_uuid.uuid4()), "parentID": t["ID"], "parentType": "node",
                            "type": "wysiwyg-text", "ordering": "a0", "status": "publish", "data": {"text": ""}}]
        return out

    def test_rebuild_of_unchanged_rich_spec_is_zero(self):
        live = self.as_stored(self.flat(self.rich_tree(), "L"))
        same, struct, updates, notes = self.sn.plan(self.flat(self.rich_tree(), "S"), "S", live, "L")
        self.assertTrue(same, struct)
        self.assertEqual(updates, [], [(u[0]["_key"], u[2]) for u in updates])
        self.assertTrue(any("inserted itself" in n for n in notes), notes)

    def test_one_real_edit_in_rich_spec_is_one_update(self):
        live = self.as_stored(self.flat(self.rich_tree(), "L"))
        same, struct, updates, _ = self.sn.plan(self.flat(self.rich_tree(title="Changed"), "S"), "S", live, "L")
        self.assertTrue(same, struct)
        self.assertEqual([(u[0]["type"], u[2]) for u in updates], [("wysiwyg-text", ["text"])])

    def test_extra_node_with_attr_is_structural(self):
        live = self.as_stored(self.flat(self.rich_tree(), "L"))
        root = next(n for n in live if (n.get("data") or {}).get("attrID") == "r-root")
        live.append({"ID": "extra-1", "parentID": root["ID"], "parentType": "node", "type": "div",
                     "ordering": "z9", "status": "publish", "data": {"attrID": "someone-elses"}})
        same, struct, _, _ = self.sn.plan(self.flat(self.rich_tree(), "S"), "S", live, "L")
        self.assertFalse(same)
        self.assertTrue(any("only on the site" in s for s in struct), struct)

    def test_attr_filter_limits_scope(self):
        live = self.as_stored(self.flat(self.rich_tree(), "L"))
        spec = self.flat(self.rich_tree(title="T2", body="B2"), "S")
        _, _, all_updates, _ = self.sn.plan(spec, "S", live, "L")
        _, _, only, _ = self.sn.plan(spec, "S", live, "L", {"r-body"})
        self.assertEqual((len(all_updates), len(only)), (2, 1))

    def test_normalisers(self):
        self.assertEqual(self.sn.css_norm("a: 1px , 2px;b:c ;"), self.sn.css_norm("a:1px,2px;b:c"))
        self.assertEqual(self.sn.svg_norm('<svg width="9" b="2" a="1"><g/></svg>'),
                         self.sn.svg_norm('<svg a="1" b="2" height="9"><g/></svg>'))
        self.assertNotEqual(self.sn.svg_norm('<svg a="1"><path d="M0"/></svg>'),
                            self.sn.svg_norm('<svg a="1"><path d="M1"/></svg>'))

    def test_override_shell_counter(self):
        shell = {"parentType": "override", "parentID": "I", "status": "publish",
                 "data": {"override": {"originalID": "X"}}}
        full = dict(shell, data={"override": {"originalID": "Y"}, "text": "kept"})
        self.assertEqual(self.sn.all_shell_instances([shell, dict(shell)]), 1)
        self.assertEqual(self.sn.all_shell_instances([shell, full]), 0)


class DirectoryEdition(unittest.TestCase):
    """directory-plugin/ is generated by scripts/build_directory.py for the Claude plugin
    directory: Markdown, JSON and an icon only, nothing that reads like a server login or
    a credential, and never edited by hand."""

    def test_in_sync_and_clean(self):
        # no scripts/__pycache__: scripts/ ships in the npm package
        sys.dont_write_bytecode = True
        sys.path.insert(0, os.path.join(ROOT, "scripts"))
        import build_directory as bd
        want = bd.build()                       # raises on a forbidden word, file type or size
        self.assertEqual(bd.differences(want, bd.existing()), [],
                         "run python scripts/build_directory.py")
        # GitHub is what the directory reads: every generated file must be committed
        self.assertEqual(bd.untracked(want), [], "git add directory-plugin (check .gitignore)")
        for rel in want:
            self.assertIn(os.path.splitext(rel)[1] or rel, {".md", ".json", ".png", "LICENSE"}, rel)
        skill = want["skills/mosaic-headless/SKILL.md"].decode("utf-8")
        self.assertRegex(skill, r'(?m)^description: ".+"$')
        self.assertNotIn("userConfig", want[".claude-plugin/plugin.json"].decode("utf-8"))
        # the gate itself: each of these must be caught
        for bad in ("ssh user@host", "cat ~/.ssh/id_rsa", "edit wp-config.php", "export $API_KEY",
                    "os.environ['TOKEN']", "Cookie: wordpress_logged_in_x", "X-WP-Nonce: 1",
                    "an application password", "https://mosaic." + "moksaweb.com/"):
            self.assertTrue(bd.FORBIDDEN.search(bad), bad)
        for fine in ("setCookie action", "a design token", "the cookie condition"):
            self.assertFalse(bd.FORBIDDEN.search(fine), fine)


class DataFiles(unittest.TestCase):
    def test_row_counts_match(self):
        text = read("references/data-files.md")
        checked = 0
        for path, n in re.findall(r"^\| `(data/[^`]+)` \| (\d+) +\|", text, re.M):
            full = os.path.join(ROOT, path)
            if os.path.isdir(full):
                got = sum(len(rows(os.path.join(path[5:], f))) for f in os.listdir(full) if f.endswith(".csv"))
            else:
                got = len(rows(path[5:]))
            self.assertEqual(got, int(n), path)
            checked += 1
        self.assertGreater(checked, 40)

    def test_no_demo_host_or_server_ids(self):
        # the demo site's host and its hosting ids must not ship (Claude directory
        # review; skill README rules). Built from parts so this file does not match.
        bad = ["mosaic." + "moksaweb.com", "1469" + "814", "6656" + "199", "159.65." + "134.149"]
        tracked = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True,
                                 text=True).stdout.split("\0")
        hits = []
        for rel in filter(None, tracked):
            path = os.path.join(ROOT, rel)
            if not os.path.isfile(path) or rel.endswith((".png", ".jpg", ".ico")):
                continue
            with open(path, encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
            hits += ["%s: %s" % (rel, b) for b in bad if b in text]
        self.assertEqual(hits, [])

    def test_pending_columns(self):
        r = rows("pending.csv")
        self.assertTrue(r)
        self.assertEqual(set(r[0]), {"date", "question", "why_not_found", "asked_by", "status"})


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=1).result
    n = result.testsRun
    bad = len(result.failures) + len(result.errors)
    print("\n%d/%d passed" % (n - bad, n))
    sys.exit(1 if bad else 0)
