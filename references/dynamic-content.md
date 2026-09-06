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
