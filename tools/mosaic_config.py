#!/usr/bin/env python3
"""Where a tool gets the site URL and the REST session, in one place.

Every tool here talks to ONE WordPress site over its REST API, and needs three
things to do it: the site's base URL, a logged-in cookie, and a matching
`wp_rest` nonce. `tools/mint_session.php` prints all three from WP-CLI on the
server; nothing here ever goes looking for them.

Two ways to supply them, and the environment wins:

    MOSAIC_SITE_URL     https://example.com
    MOSAIC_REST_COOKIE  wordpress_logged_in_…=…
    MOSAIC_REST_NONCE   0a0326da96
    MOSAIC_THEME_ID     the theme uuid, when a tool needs one

or a JSON file passed with `--config`:

    {"base": "https://example.com", "cookie": "…", "nonce": "…",
     "themeID": "…", "version": "1.0.9"}

The environment path exists so the credential never has to be written to disk at
all. When this skill is installed as a plugin, its `userConfig` prompts for these
values - the cookie and the nonce declared `sensitive: true`, so Claude Code masks
them and keeps them in the platform's credential store rather than in
`settings.json` - and the user exports them for the tool run. A value is asked
FOR, never read from wherever the user happened to leave it.

The file is still supported because a sweep over a scratch site is easier to
repeat from one, and because `--config` is what every example in this skill shows.
Nothing in either path is sent anywhere but the site named in `base`.
"""
import json
import os

ENV = {
    "base": "MOSAIC_SITE_URL",
    "cookie": "MOSAIC_REST_COOKIE",
    "nonce": "MOSAIC_REST_NONCE",
    "themeID": "MOSAIC_THEME_ID",
    "version": "MOSAIC_VERSION",
}

REQUIRED = ("base", "cookie", "nonce")


def load(path=None, require=REQUIRED):
    """Return the config dict, environment over file.

    `path` may be None, in which case the environment has to carry everything.
    A missing required key is a hard error naming both ways to supply it, rather
    than a KeyError five frames deep in a request.
    """
    cfg = {}
    if path:
        with open(path, encoding="utf-8") as fh:
            cfg = json.load(fh)
    for key, var in ENV.items():
        value = os.environ.get(var)
        if value:
            cfg[key] = value

    missing = [k for k in (require or ()) if not cfg.get(k)]
    if missing:
        raise SystemExit(
            "missing %s.\n"
            "Supply them in the environment (%s) or in a JSON file passed with "
            "--config.\n"
            "`php tools/mint_session.php` run through WP-CLI on the site prints a "
            "cookie and a matching nonce."
            % (", ".join(missing), ", ".join(ENV[k] for k in missing)))
    return cfg
