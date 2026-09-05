# How Mosaic fails, measured

Every failure below was produced on purpose, on a live install, by the sweep in
`tools/sweep_node_types.py`. None of it is inferred from source.

## Mosaic does not validate placement at commit time

This is the fact that shapes everything else. Mosaic's commit endpoint will happily
store a node whose parent makes no structural sense. The rejection happens later, at
**render** — and it takes the entire page with it.

Placing `accordion-item` directly under a `div`:

```
commit  -> HTTP 200, syncResponseEnvelopes with action "create". The row is in the DB.
render  -> HTTP 200, 54 bytes, body: "AccordionElementMResource instance required"
```

Not a 500. Not a WordPress error page. A **200 with a plain string where the site used
to be**. Three of the 74 free types do this from a plain `div` parent:

| type | what the dead page says |
|---|---|
| `accordion-item` | `AccordionElementMResource instance required` |
| `accordion-content` | `AccordionItemElementMResource instance required` |
| `wysiwyg-variable` | `NodeMResourceFilterFunctionInterface parent is missing` |

The consequence for anything automated: **a successful commit is not evidence of a
working page.** Fetch the page and check its size after writing. A monitor that only
watches status codes will report a healthy site that is serving 54 bytes.

It also means a batch write is dangerous in a way it is not in Elementor or Gutenberg:
one bad node does not degrade its own corner of the page, it deletes the page. Write
one subtree, verify, then write the next.

## Some types kill the commit request itself

Five free types return **HTTP 500** from `/commit` when placed under a `div`:

```
component-instance   loop   loop-items   loop-pagination-numbers   loop-pagination-number
```

These are the types that require a resolved context — a component to instantiate, a
query to iterate — and the constructor throws before Mosaic can turn the problem into
a normal validation response. Nothing is written, so a 500 here is *safer* than the
silent 200 above, but it is still a PHP fatal in the error log rather than an
error message you can show a user.

`document` produced a 502 on one run and a 500 on another: the same fatal, sometimes
surfacing as a gateway timeout instead. Treat 5xx from `/commit` as one class.

## Validator rejections arrive as HTTP 200

Separate from both cases above: when Mosaic *does* reject a value cleanly, it answers
`RESTJSONExceptionEnvelope` — HTTP **200** with an `exceptions` array in the body.

```python
resp = commit(...)          # 200
resp["response"]["exceptions"]   # <- the actual verdict lives here
```

So there are three distinct outcomes and only one of them changes the status code:

| what happened | status | how you detect it |
|---|---|---|
| clean validator rejection | 200 | `exceptions` in the body |
| PHP fatal during commit | 500/502 | status code |
| structurally invalid node accepted | 200 | **nothing, until you fetch the page** |

## Commit has side effects beyond the rows you sent

The first commit against a fresh theme came back having created things nobody asked
for:

```
create breakpoint      _t
create breakpoint      _m
create collection      9083a14b-…
create collectionMode  9a674a81-…
create collectionSkin  e4beb80a-…
```

`heal()` runs as part of the commit path, so the response's `syncResponseEnvelopes`
can contain resources from managers you never touched. Read the whole envelope list
and take every revision in it — assuming the response only describes your own writes
will leave you holding stale revisions for the rest of the session.

Composite types heal aggressively too: a naive batch that placed all 74 types once
produced **802 node rows**, because types like `accordion` and `navbar` build their
required children on commit.

## `modified_gmt` is server-assigned

A record committed with `"modified_gmt": "2026-09-05 17:00:00"` came back stored as
`16:59:16`. The server overwrites it. Do not use a value you sent as a local cache key.

## Reproducing all of this

```bash
wp eval-file tools/bootstrap_probe_theme.php          # licence-free scratch theme
python tools/sweep_node_types.py --config sweep.json --setup
python tools/sweep_node_types.py --config sweep.json --sweep
```

The sweep is destructive by design and must only be pointed at a scratch site.
