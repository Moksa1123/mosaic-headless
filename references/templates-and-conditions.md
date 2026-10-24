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

**On 1.0.10 an auto template is an ordinary, writable template.** Earlier releases
measured two limits here - `adminTemplateEditorInstance` did not list auto templates,
and their document had no `template-internal` root, so there was no route to putting
content in one. Re-measured on 1.0.10, both are gone:

```
POST theme/<themeID>/adminTemplateEditorInstance/commit
revisionEnvelopes.template = [{"newRevisionRecord": {
    "ID": "<uuid you mint>", "parentType": "", "parentID": "", "ordering": "a0",
    "status": "publish", "revision": "", "version": "", "name": "Search",
    "masterID": "<master>", "assign": "auto", "path": "search.php",
    "conditions": []}, "originalRevisionRecord": null}]
```

answers 200; the template's document already holds one node, the
`template-internal` root the server created; `build_site.build_page_document()`
writes a tree under it like any page's; and `/?s=…` renders it. The template is
listed by `adminTemplateEditorInstance` and is deleted the same way, with
`status: "delete"`. This is the commit the editor's own "add template" dialog sends -
`createAutoTemplate` is the post-type case only. Any path from the hierarchy works the
same way: `search.php`, `404.php`, `archive-<type>.php`, `taxonomy-<tax>.php`.

An auto template is not in `template_assigns` - it binds by path - so a clean-up that
deletes "templates nothing is assigned to" deletes it. Recreate it after any such
prune.

**`post/<id>` is the only resourceQuery `createManualTemplate` accepts.** The grammar in
`ResourceQuery::create()` is just `explode('/', $s, 2)`, so anything parses - but the
only resource type any template path registers is `post`
(`setResourceType('post')` in PathPostTypePage, PathPostTypePost and PathPostTypes).
`path/single-page.php` and `path/index.php` were both tried against the live
endpoint and both returned HTTP 500. So this endpoint has no catch-all; the catch-all
is the `assign:"auto"`, `path:"index.php"` row above (the editor's **Fallback → Empty**
template). Without one, a URL with no template of its own gets `status_header(406)`
and an empty body.

**Which auto template wins.** Candidates are ordered first by how specific the path
is, then by the row's `ordering` string (`ORDER BY FIELD(path, …) ASC, BINARY
ordering ASC`, `TemplatesRevisionModel`), and the first one whose conditions match is
used (`LocatedTemplateRenderMResourceManager`). Two auto templates on the same path -
say a conditioned single-post layout and the plain one - need the conditioned one to
carry the LOWER `ordering`, or the unconditioned one always wins. This is the
editor's drag-to-reorder. The editor's fallback types map to paths as Single →
`single.php`, Archive → `archive.php`, Homepage → `front-page.php`, Empty →
`index.php`. Masters order the same way: the first master by `ordering` is the one
a new template is offered by default.

**A template_assigns row with empty `parentID` and `parentType` binds nothing.** It is
what the editor writes for "Auto template" (`TemplateAssign` treats it as
auto-assigned and `Post::getAssignedTemplateID` skips it), so do not count it as a
manual binding.

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
          "subject": {"type": "httpGet",
                      "httpGetOptions": {
                        "settings":   {"name": "show"},
                        "comparator": {"type": "text",          // INSIDE <type>Options
                                       "textOptions": {"operator": "equals",
                                                       "settings": {"value": "yes"}}}}}
        }
      }
    ]
  }
]
```

The `<id>Options` suffix is the same convention as everywhere else in Mosaic
(`RuleTypeAbstract::getOptionsDataName()` returns `getID() . 'Options'`).

**The comparator lives inside the subject's options**, beside `settings`, not beside
`subject`. The validator reads it as `subject.<type>Options.comparator`
(`ValidatorEvaluator.php`) and so does the evaluator (`RuleTypeAbstract.php`:
`$subjectData->{$subjectType . 'Options'}->comparator`). Put it one level up and the
evaluator finds no comparator and calls
`SubjectMeta::getLocalOrGlobalComparatorMetaByID(null)`, which is a PHP fatal
(`Undefined property $comparator`) that takes the WHOLE page down, not just the
element. Reported from a client build on 1.0.10 and confirmed in the source; the post
loop filters in `references/dynamic-content.md` use the same nesting.

"Show only when a field has a value", as it ran on a client site on 1.0.10:

```json
{"uuid": "<uuid>", "type": "serverCondition", "serverConditionOptions": {"subject": {
  "type": "variable", "variableOptions": {
    "settings": {"dynamicCode": "@VAR('post/meta_x')"},
    "comparator": {"type": "text", "textOptions": {
      "operator": "regexp", "settings": {"value": "/./"}}}}}}}
```

- **`dynamicCode` is a plain string.** The `variable` subject hands its setting
  straight to the evaluator; `{"v": "@VAR(…)"}` there reaches
  `LocalContext::evaluateDynamicCodeToStringOrArray()` as a `stdClass` and is a
  page-wide fatal. (A post loop FILTER value is the opposite: it is `{"v": …}`.)
- **`regexp` needs its delimiters here.** `ServerConditionComparatorText` passes the
  value to `preg_match()` as the whole pattern, so it is `/./`, not `.`. A pattern
  without delimiters makes `preg_match` return false, which is read as "no match":
  the element disappears on every page and nothing is reported. A post loop filter's
  `regexp` is the opposite again - it becomes SQL `REGEXP` and takes NO delimiters
  (`FilterSubjectPostTypes.php`).
- Units in one group AND: `regexp /./` plus `not-contains` on the same variable is
  "has a value and is not X".
- Inside a `wpPostType` loop, `@VAR('<loopNamespace>/meta_x')` evaluates per item, so
  each row shows or hides on its own field.

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

## Multilingual sites

Mosaic has no front-end translation of its own, and no condition subject for the
current language: the taxonomy subjects list only `public` taxonomies
(`ServerConditionSubjectTaxonomies`), Polylang's `language` taxonomy is not public,
and WPML does not use a taxonomy at all. There is no WPML or Polylang code anywhere in
the 1.0.11 plugin. What the official docs (Translation page) describe, and what the
data model supports:

- **Per-language copies of manual templates.** Each translation is its own post, so
  bind it to its own template (`createManualTemplate`) holding the translated text.
  Header and footer live on the master, so a translated header means a translated
  master, used by that language's templates. Text inside templates does not reach
  WPML String Translation.
- **Auto templates are shared by every language** - archive, search, 404, the
  fallbacks. Keep their text in `@VAR` output or the post content, not literals.
- **Post content translates for free.** `wpContent` prints the editor content of the
  current post, which the translation plugin already swapped, so a page whose words
  live in the WordPress editor needs one template for all languages.
- **Loops follow the language.** WPML filters the query, so a `loop` lists only the
  current language's posts; untranslated posts show only with WPML's "fallback to
  default language" per post type.
- **Language switcher** goes in a `wpShortcode` (`[wpml_language_switcher]`); Polylang
  ships no shortcode.
- TranslatePress (which translates the rendered page) is the plugin the Mosaic team
  recommends; it needs none of the above.

`<html lang>` comes from `get_locale()` (`Common/SiteLanguage.php`), which the
translation plugins filter per request - not measured here. Bidi: RTL sites are
supported, but Tabs' arrow keys and Slider swiping are not mirrored on the front end.

## Verification status

The routing rules and the condition grammar above are read from source and from the
live metas endpoints. Element conditions (`node.data.conditions`) have been driven end
to end on a client build on 1.0.10 with the shape above - the `variable` subject, the
`text` comparator's `regexp` and `not-contains`, inside and outside a post loop. Other
subjects are read from source only; build one, then read the row back and diff it
against what you sent. A wrong shape is either silently dropped or a fatal on render,
so load the page after every condition you commit.
