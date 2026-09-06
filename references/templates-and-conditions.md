# Templates, routing and conditions

## How Mosaic decides which template renders

A Mosaic template row carries `assign`, `path` and `conditions`, and those three
answer the whole routing question. From
`LocatedTemplateRenderMResourceManager`:

```php
if ($templateRevisionRecord->getAssign() == 'auto'
    && in_array($templateRevisionRecord->getPath(), $paths)
    && $templateRevisionRecord->matchConditions()) { … }
```

So there are exactly two routing modes:

| `assign` | how it is chosen |
|---|---|
| `auto` | `path` must be in the WordPress template hierarchy for the current request, **and** `conditions` must match |
| `manual` | bound to one specific post through a row in `mosaic_template_assigns`; `conditions` are not consulted |

`path` values come from `GET /template-path-dictionary` — `single-page.php`,
`single-post.php`, `archive-post.php`, `taxonomy-category.php`, `author.php`,
`single-product.php`, `archive-product.php` and so on. It is the WordPress template
hierarchy, so a Mosaic template lands wherever the corresponding PHP template would.

**`assign` + `path` is the other binding, and it is a real catch-all.** The
template row carries `assign` (default `auto`) and `path` columns. Commit one with
`assign:"auto"`, `path:"index.php"` and it binds to a template path rather than to a
post; `X-Mosaic-Paths` on a 406 names the paths Mosaic looked for, and `index.php` is
in all of them. Measured A/B: a URL with no template returned 406, was handled once
the row existed, and returned to 406 when it was deleted.

Two limits, both measured: `adminTemplateEditorInstance` does not list auto templates,
and their document has no `template-internal` root - `heal()` builds that only for
templates created through `createManualTemplate`, and committing one directly answers
HTTP 500. So the row stops the 406 but there is no verified route to putting content
in it.

**`post/<id>` is the only resourceQuery `createManualTemplate` accepts.** The grammar in
`ResourceQuery::create()` is just `explode('/', $s, 2)`, so anything parses - but the
only resource type any template path registers is `post`
(`setResourceType('post')` in PathPostTypePage, PathPostTypePost and PathPostTypes).
`path/single-page.php` and `path/index.php` were both tried against the live
endpoint and both returned HTTP 500. There is no catch-all: a URL with no template
of its own gets `status_header(406)` and an empty body.

**Manual assignment is a REST call, not a commit.** `POST /templateAssign/createManualTemplate`
with `resourceQuery=post/<postID>` and `masterID=<masterID>` creates the template row
*and* the assign row in one step, deriving the path and name from the post. The eight
pages built by `tools/build_site.py` are all bound this way.

One consequence worth knowing: **that endpoint creates a new template every time.**
Calling it twice for the same post leaves two template rows and one assign row —
`tools/build_all.py` resets the theme before rebuilding for exactly this reason.

## The condition structure

The same shape drives template routing, element visibility (`node.data.conditions`),
interaction gating and form actions — four contexts, one grammar.

```jsonc
"conditions": [                              // groups are OR-ed
  {
    "uuid": "<uuid>",
    "evaluationUnits": [                     // units within a group are AND-ed
      {
        "uuid": "<uuid>",
        "type": "serverCondition",
        "serverConditionOptions": {
          "subject":    {"type": "httpGet",
                         "httpGetOptions": {"settings": {"name": "show"}}},
          "comparator": {"type": "text",
                         "textOptions": {"operator": "equals",
                                         "settings": {"value": "yes"}}}
        }
      }
    ]
  }
]
```

The `<id>Options` suffix is the same convention as everywhere else in Mosaic
(`RuleTypeAbstract::getOptionsDataName()` returns `getID() . 'Options'`).

**An empty or absent `conditions` matches.** `matchConditions()` returns `true` when
the evaluation yields null, so a template with no conditions always applies and an
element with none always renders. Conditions subtract, they never add.

## What you can test

Two tables, both read off the running site rather than the source:

- `data/condition-subjects.csv` — 59 subjects across four contexts (`element`,
  `template`, `interaction`, `formAction`), each with its `settingsFields` and the
  group it belongs to (`editor`, `http`, `currentUser`, `post`, `product`, `page`,
  `attachment`).
- `data/condition-comparators.csv` — 12 comparator rows with their operator sets:

| comparator | operators |
|---|---|
| `text` | equals, not-equals, contains, not-contains, starts-with, regexp |
| `number` | equals, not-equals, greater-than, greater-than-or-equal, less-than, less-than-or-equal |
| `date` | after, before |

`date` exists only in `serverCondition`. The `interaction` context additionally has a
`browserCondition` rule type whose `text` comparator drops `regexp` — browser-side
evaluation is a reduced subset, so a rule that works in a template will not
necessarily work as an interaction gate.

Most subject settings fields carry `supportDynamic: true`, meaning the value itself
can be an `@` expression rather than a literal — see `references/dynamic-content.md`.

## Verification status

The routing rules and the condition grammar above are read from source and from the
live metas endpoints. **Committing a condition has not been driven end to end** — the
property sweep's naive string probe on `conditions` returns HTTP 500, which is
consistent with the nested shape being required but is not proof the shape above is
accepted. Build one, then read the row back and diff it against what you sent; on this
data model that diff is the only error message you get
(`references/interactions.md` explains why).
