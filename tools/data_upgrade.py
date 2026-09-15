#!/usr/bin/env python3
"""Run Mosaic's plugin data upgrade from outside wp-admin.

After the plugin files move to a newer version (wp plugin install ... --force, or a
folder swap), the STORED data still carries the old dataVersion and Mosaic refuses to
run until the upgrade flow has walked its milestones. wp-admin drives that flow from
the AppMosaicAdminDataUpgrade screen; this drives the same REST route.

The route lives in its own namespace, `mosaic/<DATA_VERSION>/<VERSION>/upgrade` (no
`v` prefix, unlike the editor API), and is the same milestone protocol theme_zip.py
speaks: POST once to Start, then POST {processingID, milestoneID} per milestone until
`isCompleted`. Every batch of the upgrade (Upgrade-<version>.php) is one or more calls.

    python tools/data_upgrade.py mk.json            # upgrade to the installed version
    python tools/data_upgrade.py mk.json --status   # just report both versions

`mk.json` needs base/cookie/nonce (tools/mint_session.php mints them) and, on a
multisite, `siteID` (defaults to 1); its `version`
is only rewritten on success, because the editor API namespace changes with it.
"""
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from theme_zip import Flow  # noqa: E402


def versions(cfg):
    """(running editor versions, upgrade namespaces) read off the REST index.

    The editor namespace is registered as a regex (`mosaic/v(?P<mosaicVersion>...)`),
    so the version is read from the sibling `mosaic/v<version>/pluggable/endpoint`
    namespace, which only exists while Mosaic is actually running. The upgrade
    namespace `mosaic/<dataVersion>/<version>` is registered whenever the layer
    loads - its presence alone does not mean an upgrade is pending; a missing
    editor namespace does."""
    req = urllib.request.Request(cfg["base"].rstrip("/") + "/wp-json/?t=" + str(os.getpid()))
    req.add_header("Cookie", cfg["cookie"])
    with urllib.request.urlopen(req, timeout=60) as r:
        ns = json.loads(r.read().decode("utf-8")).get("namespaces", [])
    editor = [m.group(1) for n in ns for m in [re.fullmatch(r"mosaic/v([\d.]+)/pluggable/endpoint", n)] if m]
    upgrade = [n for n in ns if re.fullmatch(r"mosaic/[\d.]+/[\d.]+", n)]
    return editor, upgrade


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    path = sys.argv[1]
    cfg = json.load(open(path, encoding="utf-8"))
    editor, upgrade = versions(cfg)
    print("editor running    : %s" % (", ".join("v" + v for v in editor) or "- (data upgrade pending)"))
    print("upgrade namespace : %s" % (", ".join(upgrade) or "-"))
    if "--status" in sys.argv or editor or not upgrade:
        return
    data_version, plugin_version = upgrade[0].split("/")[1:]
    url = "%s/wp-json/%s/upgrade" % (cfg["base"].rstrip("/"), upgrade[0])
    print("upgrading data %s -> plugin %s" % (data_version, plugin_version))
    # siteID is the blog ID (1 on a single site); the flow refuses to start without it.
    Flow(cfg).run(url, {"siteID": str(cfg.get("siteID", 1))})
    editor, upgrade = versions(cfg)
    if not editor:
        sys.exit("editor namespace still missing after the run - check wp-admin > Mosaic")
    cfg["version"] = plugin_version
    json.dump(cfg, open(path, "w", encoding="utf-8"), indent=1)
    print("done - %s now serves v%s; %s version set to %s"
          % (cfg["base"], ", ".join(editor), os.path.basename(path), plugin_version))


if __name__ == "__main__":
    main()
