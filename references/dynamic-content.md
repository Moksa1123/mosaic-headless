# Dynamic content: the `@` expression language

Mosaic's answer to Elementor's dynamic tags. Verified end to end — every example on
this page was committed to a live site and read back out of the delivered HTML.

## The syntax you would not guess

A bare identifier does **nothing**. `Evaluator::exec()` handles the `Identifier` node
by returning the literal string `"Identifiers are not used currently"`. So this:

```
@post.title
```

is stored happily, renders as the text `@post.title`, and looks like a typo in your
content rather than a broken feature.

The real form is a **function call named `VAR`, taking a `namespace/name` string**:

```
@VAR('post/title')          ->  Probe lab
@VAR('post/id')             ->  20
@VAR('post/permalink')      ->  https://example.com/probe-lab/
@VAR('site/name')           ->  example.com
```

Expressions compose, and the 19 evaluator functions take `@VAR(...)` results as
arguments:

```
@concat('[', @VAR('post/title'), '] #', @VAR('post/id'))   ->  [Probe lab] #20
@substr(@VAR('post/title'), 0, 5)                          ->  Probe
@fallback(@VAR('post/nope'), 'DEFAULTED')                  ->  DEFAULTED
```

A literal `@` in ordinary text needs escaping as `\@`.

`@VAR_RAW('…')` is the same lookup **without HTML-escaping**. The evaluator escapes
untrusted (request-derived) values at the point of interpolation and carries a
`{value, trusted}` envelope to do it; `VAR_RAW` opts out of that. Use `VAR` unless you
are deliberately publishing markup from a trusted field.

## Where an expression goes

**Inline in text** — a `wysiwyg-variable` node inside a `text` node, with the
expression as a plain string in `dynamicCode`:

```json
{"type": "text", "data": {"tagName": "p"},
 "children": [{"type": "wysiwyg-variable", "data": {"dynamicCode": "@VAR('post/title')"}}]}
```

`wysiwyg-variable` is one of the seven types that **kill the page** when placed under
a plain container — it needs a wysiwyg parent, and the sweep recorded it as
`NodeMResourceFilterFunctionInterface parent is missing`.

**On a property** whose validator chain includes `ValidatorDynamicCodeObject` — a
button's `url`, an image's `src`, and so on. There the value is an object, because a
literal is also legal in that slot and the object is what disambiguates:

```json
"url": {"v": "@VAR('post/permalink')"}
```

Two different shapes for the same language, and which one applies is decided by the
property's validator chain in `data/node-properties.csv`: **`ValidatorDynamicCode`
means a bare string, `ValidatorDynamicCodeObject` means `{"v": "…"}`**.

Getting it wrong on a URL is silent and looks like a broken link rather than a broken
expression. `menu-link`'s `url` chain is `ValidatorDynamicCodeObject → ValidatorURL →
ValidatorUrlObject`; given a bare `"@concat('/contact/?ref=', @VAR('post/title'), '#consult')"`
it commits without complaint and delivers
`href="http://concat('/contact/?ref=%27…"` - the leading `@` dropped and the rest taken
as a URL (measured on a client build on 1.0.10). As `{"v": "@concat(…)"}` it delivers the evaluated link.


## The variable namespace

`data/dynamic-variables.csv` — 74 variables across 11 namespaces, each row carrying
the exact `@VAR('…')` expression to paste:

| namespace | n | what it needs to resolve |
|---|---|---|
| `post` | 22 | a post/page context — `title`, `id`, `permalink`, `content`, `featuredImage`, `publish_date`, `author_name`, `modified_timestamp`, … |
| `user` | 13 | the current visitor — `displayName`, `email`, `loggedin`, `user_registered_date`, … |
| `site` | 7 | always — `name`, `url`, `description`, `admin_email`, `wpurl` |
| `author` | 7 | a post context |
| `menu` | 7 | inside a menu loop — `href`, `title`, `hasChildren` |
| `request` | 4 | always — `ip`, `page_url`, `referrer`, `user_agent` |
| `slider` | 4 | inside a slider |
| `wordpress_search` | 4 | a search results page — `searchQuery`, `resultCount` |
| `wordpress_archive` | 3 | an archive page |
| `form` | 2 | inside a form action |
| `__current_theme` | 1 | always |
| `row` | — | inside a loop; its schema is declared per loop source, not statically |

**An unresolvable name is an empty string, never an error.** `@VAR('nope/nothing')`
renders as nothing at all, and so does a real name in the wrong context — a
`post/title` on a page with no post context is indistinguishable from a typo. That is
what `@fallback()` is for, and why a blank spot on a page is the symptom to look for
rather than a message in a log.

The name separator is `/` (`TemplatingContextVariable::VARIABLE_SEPARATOR`), and the
namespace is everything before the first one.

## The functions

`data/evaluator-functions.csv` — 19 of them with their arity:

```
abs(1)  round(1)  round_up(2)  calc(1)  sum(…)  avg(…)          numeric
concat(…)  substr(3)  excerpt(4)  remove_html(1)                text
esc_attr(1)  esc_html(1)  json_encode(1)                        escaping
date(3)                                                         dates
fallback(…)                                                     defaulting
attachment(2)  find_image(2)  find_link(2)  find_video(2)       media
```

`sum`, `avg`, `concat` and `fallback` are variadic. `date()`'s timestamp argument is a
true GMT Unix timestamp — pair it with `post/publish_timestamp_gmt`, not
`publish_timestamp`, unless you want the local-time value re-interpreted as UTC.

## A loop in place of a component's children

Three component families take a loop INSTEAD of hand-authored children, which is
the thing a page builder needs a plugin per component to do:

```
slider-slides > slider-loop-slides  > slider-slide      one slide per row
tabs-menu     > tabs-loop-tabs      > tabs-tab
tabs-content  > tabs-loop-tab-panes > tabs-tab-pane
list          > list-loop-items     > list-item
accordion     > accordion-loop-items> accordion-item
```

Each loop container carries the same three keys an ordinary `loop` does —
`loopType`, `loopNamespace` and a `<loopType>Options` group — and the template
inside reads its row with `@VAR('<namespace>/…')`. You author ONE slide, one tab,
one row; the count comes from the content. The assertion that matters is therefore
a COUNT: a template that failed to loop renders exactly once and looks correct.

**`canBeParentFor` disagrees with the factory's own default data on these.**
`SliderLoopSlidesElementTypeFactory::canBeParentFor()` returns true for
`SliderSlidesElementTypeFactory` — the track, not the slide — while its
`getDefaultData()` seeds itself with a `slider-slide`. `accordion-loop-items` says
`accordion` the same way. The structure the editor actually builds is the second
one. `build_page.py` resolves it by treating a loop container as standing in for
its parent's children: what `slider-loop-slides` accepts is what `slider-slides`
accepts.

## Filtering and ordering a post loop

A `wpPostType<Type>` loop takes `filters` (the condition structure of
`references/templates-and-conditions.md`: units in one `evaluationUnits` group are
AND-ed, groups are OR-ed) and `orderByClauses`. The filters are evaluated in the
context the loop sits in, so inside a single-post template `@VAR('post/…')` is the
post being viewed. Subject IDs are built from WordPress names, camel-cased after
every `-`, `_` or space (source: `FilterSubjectPostTypes.php`):

| subject | id | operators | value |
|---|---|---|---|
| the posts themselves | `postType<Type>` (`postTypeWork`) | `includes` / `excludes` | a list of post ids; dynamic |
| a taxonomy | `taxonomy<Taxonomy>` (`taxonomyWorkCategory`) | `includes` / `excludes` | term ids; dynamic |
| a meta key | `postType<Type>PostMeta`, `settings.key` | the comparator you pick: `text`, `number`, `date` | per comparator |

A dynamic filter value is `{"v": …}` - the field declares `SupportDynamic`, which the
reader validates with `ValidatorDynamicCodeObject`. "More work in the same category,
not this one", measured on a client build on 1.0.10:

```json
{"uuid": "<uuid>", "type": "filter", "filterOptions": {"subject": {
  "type": "postTypeWork", "postTypeWorkOptions": {"settings": {}, "comparator": {
    "type": "postTypeWork", "postTypeWorkOptions": {
      "operator": "excludes", "settings": {"value": {"v": "@VAR('post/id')"}}}}}}}}
```

with a second unit in the same group on `taxonomyWorkCategory`, operator `includes`,
value `{"v": "@LOOP('post/work_category', 1, 'term_id')"}`. A Meta Box checkbox
(stored `"1"`) filters as subject `postTypeWorkPostMeta` with
`settings: {"key": "work_featured"}` and a `text` comparator
`{"operator": "equals", "settings": {"value": "1"}}` - six posts back, in order.

`orderByClauses` accepts `random`: `{"type": "random", "uuid": "<uuid>",
"randomOptions": {"settings": {}}}`, a different order on every uncached render. Under
a page cache that is one order per cache lifetime, not per visitor.

## `loop-pagination`, and the key you must not use

```
loop > loop-pagination > loop-pagination-button-previous
                       > loop-pagination-numbers > loop-pagination-number
                       > loop-pagination-button-next
```

`loop-pagination-number` is a TEMPLATE repeated per page, the same rule as a
slider bullet — author one. `loop-pagination-numbers` takes `pagesBefore` /
`pagesAfter` / `pagesStart` / `pagesEnd` to decide how much of a long range to
show.

**Do not set `paginationKey` to `p`.** It is one of WordPress's own reserved query
vars, meaning "post ID": `?p=2` answers **HTTP 301** to post 2, so the visitor
leaves the page entirely and the loop renders nothing. Measured. Any other key
works — `?notes=2` on the demo pages the archive and changes all three rows.

## `@substr` counts BYTES

`@substr(@VAR('post/title'), 0, 14)` on a Han title cuts the fifth character in
half and the output ends in U+FFFD. Lengths have to be a multiple of the encoding
width — 18 for six three-byte characters — or the truncation has to be left to CSS.
A count-based check cannot see this; `verify_components.py` looks for the
replacement character directly.

## Date conditions (1.0.10)

The `date` comparator - element and form-action server conditions, and the post /
user loop filters - has four operators now: `after`, `after-or-equal`, `before`,
`before-or-equal` (1.0.9 had the first and third). The value is any text, read by
`DateComparison` when it compares rather than validated when it is saved:

- a year first: `2026-09-24`, `2026/9/24`, `2026-09`, `2026`;
- a year last: `28/09/2026`, `9-28-2026` - a number above 12 is the day; when both
  could be, the **site's date format** decides which comes first;
- `Ymd` (ACF's date picker storage) and `YmdHis`; any shorter digit run is a Unix
  timestamp in the site timezone;
- a time after the date or on its own (`09:16`, `9:16 pm`), with an optional zone.

The less precise side sets the precision: a date against a date-time compares the
two days. Whatever cannot be read as a date matches **no** operator, so a typo is a
condition that is never true rather than an error. Loop filters compare in SQL
(`post_date_gmt` / `post_modified_gmt` as UTC, the others as the site's wall clock).

## The search results page

A `search.php` auto template (`references/templates-and-conditions.md`) has a
`wordpress_search` namespace. Measured on 1.0.10, searching a term with four matches
and one with none:

| expression | 4 results | none |
|---|---|---|
| `@VAR('wordpress_search/resultCount')` | `4` | `0` |
| `@VAR('wordpress_search/searchQuery')` | the term | the term |
| `@fallback(@VAR('wordpress_search/resultCount'), 'none')` | `4` | `none` |
| `@fallback(@VAR('wordpress_search/resultCount'), '0')` | `4` | `0` |

`resultCount` is `number_format_i18n(found_posts)` - a formatted string, so `1,234`
past a thousand, and `0` (not empty) when nothing matched. `@fallback` treats `''`,
`'0'` and `'NaN'` as empty, and returns its second argument only if THAT is truthy in
PHP, so a fallback of `'0'` can never be chosen; any other text can.

The results are a loop: `loopType: "localContext"`, `loopSource:
{"v": "@VAR('wordpress_search/results')"}` (a `@VAR`, as every loop source must be).
**Inside it each result is `item`, unless you rename it**:

| per-result expression | result |
|---|---|
| `@VAR('item/title')`, default namespace | the title |
| `@VAR('post/title')`, default namespace | empty - `post` is the page's own context, and a search page has none |
| `@VAR('post/title')` with `loopNamespace: "post"` on the loop | the title |

With `loopNamespace: "post"` every per-post expression works per result - meta,
`@LOOP('post/<taxonomy>', 1, 'term_name')`, the permalink. WordPress's own query
arguments narrow the search (`/?s=…&post_type=work&work_category=<slug>`), so a
filter bar is a set of `menu-link`s whose `url` is
`{"v": "@concat('/?post_type=work&work_category=<slug>&s=', @VAR('wordpress_search/searchQuery'))"}`
- the term survives the switch.
