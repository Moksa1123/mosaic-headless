# Releasing

npm publishing is driven by git tags - never run `npm publish` by hand. A manual
publish once raced the workflow (1.37.0 went out while a browser-auth publish was
still waiting).

## One-time setup (done)

No token anywhere: npmjs.com -> package **Settings** -> **Trusted Publisher** ->
GitHub Actions, `Moksa1123/mosaic-headless`, workflow `release.yml`. The workflow
authenticates via OIDC (`id-token: write`); provenance is automatic.

## Every release

The version bump goes through a pull request; the tag is pushed only after it is
merged, so the published version is always a commit on `main`.

```bash
# 1. checks that must pass first
python tools/test_mosaic.py
python tools/check_numbers.py
node scripts/check-release.mjs

# 2. on a branch: bump without tagging. The `version` script syncs SKILL.md, the
#    platform templates and .claude-plugin/plugin.json, and rebuilds directory-plugin/
git switch -c release-x.y.z
npm version minor --no-git-tag-version      # or patch / major
git commit -am "vX.Y.Z - <what changed>"
git push -u origin release-x.y.z
gh pr create --fill

# 3. after the PR is merged
git switch main && git pull
git tag vX.Y.Z && git push origin vX.Y.Z    # the tag triggers .github/workflows/release.yml
gh run watch
npm view mosaic-headless version            # must print X.Y.Z
```

The workflow refuses a tag that disagrees with `package.json`, runs
`scripts/check-release.mjs` and the installer smoke test, publishes, and creates
the GitHub release. A re-run of an already-published tag is a no-op.

## What "minor" means here

The package versions the **data as much as the code**. A tool's behaviour change
that callers can see (a new check that can now exit 1, a changed write), new
facts measured on a new Mosaic version, or re-extracted tables are at least a
minor bump. A patch is a fix that changes no stored shape and no table.

## After publishing

Installed copies (the global `~/.claude/skills/mosaic-headless` and the profile
copies) are refreshed separately, never as part of a release: other projects
import `build_page.py`, `build_site.py` and `sweep_node_types.py` from the
installed copy, so a refresh waits for their owners' agreement. Report the md5 of
those three files before and after any refresh.
