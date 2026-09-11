#!/usr/bin/env python3
"""Drive Mosaic's own theme export and import - the ZIP the editor's buttons make.

    python tools/theme_zip.py export --config c.json --out theme.zip
    python tools/theme_zip.py export --config c.json --theme <themeID> --out theme.zip
    python tools/theme_zip.py import --config c.json --zip theme.zip
    python tools/theme_zip.py import --config c.json --zip theme.zip --activate
    python tools/theme_zip.py import --config c.json --zip theme.zip --replace <themeID>

`theme_export.php` / `theme_import.php` move a theme as JSON rows over WP-CLI, which
is the form that diffs and versions. This is the other form: the archive Mosaic
itself produces, with the theme's attachments inside it, that the editor's Import
button understands and that a site with no shell access can still take.

Both directions are milestone flows, and the shape is the same:

  1. POST with no `processingID` -> {type:"Start", ID, milestones:[{id,name}...]}
  2. for each milestone, in order, POST {processingID, milestoneID} until the reply
     says isCompleted. A reply is JSON - unless a milestone hands back a file, in
     which case it is multipart/form-data with the JSON fields as parts and the
     file as a part named after the milestone. The export's last milestone streams
     the ZIP that way, 100MB a request.
  3. type:"error" or "batchError" ends it; the lock expires by itself.

The import has one behaviour that has to be said out loud: LEFT TO ITS DEFAULTS IT
ACTIVATES THE IMPORTED THEME AS THE LIVE SITE. `themeActivateMode` falls back to
'live' when it is missing, and `replaceThemeID` deletes the theme it names before
copying the import over it. This tool sends 'test' unless told `--activate`, which
puts the imported theme in Mosaic's admin-only test mode and leaves visitors where
they were; `--replace` is opt-in for the same reason. The upload goes up in chunks
under the same milestone, one chunk per request, `totalChunks` on each.
"""
from __future__ import annotations

import argparse
import email.parser
import email.policy
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

CHUNK = 8 * 1024 * 1024      # upload chunk; the server appends whatever arrives
TIMEOUT = 300


class Flow:
    def __init__(self, cfg):
        self.cfg = cfg
        self.api = "%s/wp-json/mosaic/v%s" % (cfg["base"].rstrip("/"), cfg["version"])

    # ── transport ────────────────────────────────────────────────────────────
    def post(self, url, fields, file=None):
        """One request. `file` is (fieldname, filename, bytes) and switches the body to
        multipart. The reply is returned as (values: dict, files: {name: bytes})."""
        if file is None:
            body = urllib.parse.urlencode(fields).encode()
            ctype = "application/x-www-form-urlencoded"
        else:
            boundary = "----mosaicHeadless" + uuid.uuid4().hex
            parts = []
            for k, v in fields.items():
                parts.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n"
                              % (boundary, k, v)).encode())
            name, fname, data = file
            parts.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"; "
                          "filename=\"%s\"\r\nContent-Type: application/octet-stream\r\n\r\n"
                          % (boundary, name, fname)).encode() + data + b"\r\n")
            parts.append(("--%s--\r\n" % boundary).encode())
            body = b"".join(parts)
            ctype = "multipart/form-data; boundary=" + boundary
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Cookie", self.cfg["cookie"])
        req.add_header("X-WP-Nonce", self.cfg["nonce"])
        req.add_header("Content-Type", ctype)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                raw, rtype = r.read(), r.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            sys.exit("HTTP %d from %s: %s" % (e.code, url, e.read().decode("utf-8", "replace")[:400]))
        return self.parse(raw, rtype)

    @staticmethod
    def parse(raw, rtype):
        if not rtype.startswith("multipart/"):
            env = json.loads(raw.decode("utf-8"))
            resp = env.get("response", env)
            errs = (env.get("notificationMessages") or {}).get("errors") or []
            if errs:
                resp = dict(resp or {}, type="error",
                            messages=[m.get("message") for m in errs])
            return resp, {}
        # Mosaic's multipart: every JSON field is a part whose body is json_encode()d;
        # the file part carries a filename. email.parser does the boundary work.
        msg = email.parser.BytesParser(policy=email.policy.default).parsebytes(
            ("Content-Type: %s\r\n\r\n" % rtype).encode() + raw)
        values, files = {}, {}
        for part in msg.iter_parts():
            name = part.get_param("name", header="content-disposition")
            fname = part.get_param("filename", header="content-disposition")
            payload = part.get_payload(decode=True)
            if fname:
                files[name] = files.get(name, b"") + payload
            else:
                try:
                    values[name] = json.loads(payload.decode("utf-8"))
                except ValueError:
                    values[name] = payload.decode("utf-8", "replace")
        return values, files

    # ── the milestone loop ───────────────────────────────────────────────────
    def run(self, url, base_fields, on_milestone=None, on_file=None):
        start, _ = self.post(url, base_fields)
        if start.get("type") != "Start":
            sys.exit("did not start: %s" % json.dumps(start)[:400])
        pid, milestones = start["ID"], start["milestones"]
        print("  processing %s, %d milestones" % (pid[:8], len(milestones)))
        for m in milestones:
            mid, label = m["id"], m["id"]
            t0, calls = time.time(), 0
            while True:
                fields = dict(base_fields, processingID=pid, milestoneID=mid)
                file = on_milestone(mid, fields, calls) if on_milestone else None
                resp, files = self.post(url, fields, file)
                calls += 1
                for name, data in files.items():
                    if on_file:
                        on_file(name, data)
                if resp.get("type") in ("error", "batchError"):
                    sys.exit("  %-34s FAILED after %d call(s): %s"
                             % (label, calls, "; ".join(resp.get("messages") or ["?"])))
                if resp.get("isCompleted"):
                    break
            print("  %-34s ok  (%d call%s, %.1fs)"
                  % (label, calls, "" if calls == 1 else "s", time.time() - t0))
        return pid


def export_theme(a, cfg):
    theme = a.theme or cfg["themeID"]
    url = "%s/wp-json/mosaic/v%s/theme/%s/export" % (cfg["base"].rstrip("/"),
                                                     cfg["version"], theme)
    out = open(a.out, "wb")
    got = {"bytes": 0}

    def on_file(name, data):
        out.write(data)
        got["bytes"] += len(data)

    print("export theme %s" % theme)
    Flow(cfg).run(url, {"themeID": theme, "simpleExport": "1" if a.simple else "0"},
                  on_file=on_file)
    out.close()
    if got["bytes"] < 4 or open(a.out, "rb").read(2) != b"PK":
        sys.exit("no archive came back (%d bytes)" % got["bytes"])
    print("wrote %s  (%d bytes)" % (a.out, got["bytes"]))


def import_theme(a, cfg):
    url = "%s/wp-json/mosaic/v%s/theme/import/upload" % (cfg["base"].rstrip("/"),
                                                         cfg["version"])
    data = open(a.zip, "rb").read()
    if data[:2] != b"PK":
        sys.exit("%s is not a ZIP" % a.zip)
    chunks = [data[i:i + CHUNK] for i in range(0, len(data), CHUNK)] or [b""]
    base = {"themeActivateMode": "live" if a.activate else "test"}
    if a.replace:
        base["replaceThemeID"] = a.replace
    print("import %s  (%d bytes, %d chunk%s, mode=%s%s)"
          % (a.zip, len(data), len(chunks), "" if len(chunks) == 1 else "s",
             base["themeActivateMode"], ", replacing " + a.replace if a.replace else ""))

    # Every milestone is driven until the server says isCompleted - including this
    # one. The first version stopped after the last chunk went up, because what
    # else was there to send; the reply to that last chunk says isCompleted:false
    # (completion is reported by the call AFTER the last batch), and a milestone
    # left uncompleted leaves its batch bookkeeping in the lock. The next
    # milestone - extract - then read that stale state, took its own batch 0 as
    # already done, skipped createNeededDirectories() and failed on the first
    # nested file with "Could not copy file." The extra call has to carry a file
    # part or the upload's execute() refuses it, so the last chunk goes up again;
    # nothing appends it, because that batch is recorded as done.
    def on_milestone(mid, fields, calls):
        if mid != "upload":
            return None
        fields["totalChunks"] = str(len(chunks))
        return ("file", os.path.basename(a.zip), chunks[min(calls, len(chunks) - 1)])

    Flow(cfg).run(url, base, on_milestone=on_milestone)
    print("imported. mode=%s - %s" % (
        base["themeActivateMode"],
        "the imported theme is now LIVE for every visitor" if a.activate else
        "visible to admins in Mosaic's test mode; the live site is unchanged"))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("--config", required=True)
    e.add_argument("--theme", help="themeID; default is the config's")
    e.add_argument("--out", required=True)
    e.add_argument("--simple", action="store_true", help="Mosaic's simpleExport flag")
    i = sub.add_parser("import")
    i.add_argument("--config", required=True)
    i.add_argument("--zip", required=True)
    i.add_argument("--activate", action="store_true",
                   help="make the imported theme the live site (default: test mode)")
    i.add_argument("--replace", metavar="THEMEID",
                   help="DELETE this theme and import over it")
    a = ap.parse_args()
    cfg = json.load(open(a.config, encoding="utf-8"))
    (export_theme if a.cmd == "export" else import_theme)(a, cfg)


if __name__ == "__main__":
    main()
