# Writing to Mosaic: the checkout / check / commit protocol

*Verified end to end against a live install: a master, a template and a text node were
created through these routes and the result asserted in the delivered HTML. See
`references/failure-modes.md` for what goes wrong and how it surfaces.*

Mosaic has no "save the page" endpoint. Every document you can edit — theme,
master, template, style guide, component, component node — is reached through an
**editor instance**, and every editor instance exposes the same four routes:

```
GET  /mosaic/v<version>/theme/<themeID>/<instance>            open  (read state)
POST /mosaic/v<version>/theme/<themeID>/<instance>/checkout   claim (take the lock)
POST /mosaic/v<version>/theme/<themeID>/<instance>/check      poll  (still in sync?)
POST /mosaic/v<version>/theme/<themeID>/<instance>/commit     write
```

All 114 routes are in `data/rest-routes.csv`; the namespace is
`/wp-json/mosaic/v<plugin version>` — **the plugin version is in the namespace**, so
the base URL changes on every Mosaic update. Read it from `mosaicOptions.rest_api_url`
on any Mosaic admin page rather than composing it yourself.

## The envelopes

Both `checkout` and `check` take one required string parameter, `syncCheckEnvelopes`
— a JSON string, not a JSON body — shaped as manager type → list of `[ID, revision]`
pairs:

```json
{"node": [["<nodeID>", "<revision>"], ...], "variant": [[...]]}
```

The `revision` is the value from the row's `revision` column when you read it. The
server compares them and returns `syncResponseEnvelopes` for anything that moved
underneath you. This is **optimistic locking, per row** — not a page-level lock — so
two callers editing different nodes of the same document do not conflict.

`commit` takes `syncCheckEnvelopes` *and* `revisionEnvelopes` (also a JSON string).
The server runs `doCommit(revisionEnvelopes)` → `pushToDB()` → and then immediately
does a fresh `doCheckout` so the response hands you the new revisions to use for
your next write. **Use them.** Reusing the pre-commit revision on the following
commit is the single most likely way to get stuck in a sync-rejection loop.

## Order of operations

```
1. GET  <instance>              read current state + revisions
2. POST <instance>/checkout     with the revisions you just read
3.      ...build your changes...
4. POST <instance>/check        optional; cheap way to detect drift before committing
5. POST <instance>/commit       with syncCheckEnvelopes + revisionEnvelopes
6.      take the revisions from the response, go to 3
```

`isCheckoutAllowed()` / `isCheckAllowed()` / `isCommitAllowed()` gate each step and
throw a bare `Not allowed!` when they fail — there is no useful error body, so if a
commit throws, check the lock (`mosaic_locks`) and the capability of the user whose
cookie you are sending before suspecting your payload.

## Authentication

These are `wp-json` routes behind a nonce, not application passwords:

```
Cookie:     the logged-in admin cookie
X-WP-Nonce: mosaicOptions.common.nonces.wp_rest
```

Both are on the Mosaic admin page (`admin.php?page=mosaic`) in the `var mosaicOptions`
blob. That blob is also where you find `mosaicEdition` (`pro` / free),
`mosaicVersion`, `mosaicDataVersion`, `license.isLicenseActive`, `siteHash`, and the
`availablePostTypes` map — read it once at the start of a session instead of probing.

## What errors look like

A failed validator does not return an HTTP error. The response is a
`RESTJSONExceptionEnvelope`: HTTP 200 with an `exceptions` array in the body. Code
that only checks the status code will report a clean save on a rejected write.
Always read `exceptions` before believing a commit landed.

## Validators coerce before they reject — a number need not arrive as a number

Silent rejection is the documented hazard, but the quieter one is silent *acceptance*
of something other than what you sent. As of 1.0.9 `ValidatorInteger` mirrors
JavaScript's `parseInt()`: it takes the leading integer and discards the rest, where
the previous release fell back to PHP's `intval()` and treated a zero result as a
failure. Measured on `textarea-input`'s `maxlength`:

| sent | stored | |
|---|---|---|
| `"12"` | 12 | |
| `" 7 "` | 7 | whitespace tolerated |
| `"0012"` | 12 | decimal, not octal |
| `"12abc"` | **12** | trailing garbage ignored |
| `"12.9"` | **12** | truncated toward zero, not rounded |
| `"1e3"` | **1** | **not** 1000 — the exponent is trailing garbage |
| `"abc"` | absent | no leading digits |
| `"-5x"` | absent | parsed fine as −5; refused by the property's own `min: 0` |

`"1e3"` is the row to remember: a value that looks numeric to a human, is numeric to
`floatval()`, and lands as 1. A typo in a unit (`"16px"` where a bare integer was
wanted) likewise stores 16 and never complains. Send integers as integers, and read
the row back when you did not.

The companion change is `ValidatorMimeType`, which now accepts any number of media
type parameters including quoted values containing spaces — so
`video/mp4; codecs="avc1.42E01E, mp4a.40.2"` is valid where 1.0.8 rejected it.

`data/value-coercion-verification.csv` has these runs, along with the `stretch`
keyword's emitted declarations.
