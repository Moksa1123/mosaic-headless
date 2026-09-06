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

**Manual assignment is a REST call, not a commit.** `POST /templateAssign/createManualTemplate`
with `resourceQuery=post/<postID>` and `masterID=<masterID>` creates the template row
*and* the assign row in one step, deriving the path and name from the post. The eight
pages in `designs/` are all bound this way.

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
