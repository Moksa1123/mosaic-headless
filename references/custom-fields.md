# Custom fields: ACF and Meta Box through `@VAR` and `@LOOP`, measured

Mosaic 1.0.8 reads custom fields through one provider-neutral core with two
providers wired in: **ACF** (free or Pro) and **Meta Box** (free; Group,
Relationships, Term/User/Settings add-ons have handlers too). Plain `post_meta`
without either plugin is read as well, as a bare string. There is no public hook to
add a provider - `CustomFields/AUTHORING.md` in the plugin says so in its first
paragraph.

Everything below was measured on a live 1.0.8 install: ACF 6.8.10 and Meta Box
5.15.0, forty fields registered in code on a page, values written with
`update_field()` / `rwmb_set_meta()`, then read back **off the delivered HTML** of
a Mosaic page built through the tables. `data/custom-fields-verification.csv`, 62
rows: 59 resolve to the value expected, 3 are empty for a reason given below.

## The names

A field with meta key `k` on the current post is

```
@VAR('post/meta_k')          the field's primary value
@VAR('post/meta_k__label')   derived properties, when the field type has them
@VAR('post/meta_k__url')
@VAR('post/meta_k__id')
@VAR('post/meta_k__title')   ACF link
@VAR('post/meta_k__target')  ACF link
```

A field that holds MANY values (checkbox, relationship, taxonomy, gallery,
image_advanced, cloneable, group, repeater) is not a variable at all. It is a
**loop**, named `loop` + key - `@LOOP('post/loopk')` - and its rows carry the same
properties under the loop node's namespace (`item` unless `loopNamespace` says
otherwise): `@VAR('item/value')`, `@VAR('item/value__label')`, `@VAR('item/index')`.
An ACF **group** is the exception in spelling: `loop-k` with a hyphen, one row, and
its sub-fields are `item/value_<subfield>` with a single underscore.

Do not guess any of this. `wp eval-file tools/list_fields.php <post_id>` prints the
exact variable and loop names Mosaic registers for that post with the value each
resolves to and the row variables of every loop - the same schema the frontend
evaluates, so a name it does not print does not exist:

```
variable post/meta_acf_po           ACF / Post object / ID     6
variable post/meta_acf_po__label    ACF / Post object / 標題   Shop
variable post/meta_acf_po__url      ACF / Post object / 網址   https://…/shop/
loop     post/loopacf_rel           ACF / Relationship         2 items; first row: value=2 | value__label=Sample Page | value__url=… | index=1
loop     post/loop-acf_group        ACF / Group                1 items; first row: value_ga=group text | value_gb=7 | index=1
```

## What each field type resolves to

| field | `meta_k` | derived |
|---|---|---|
| text, textarea, number, url, email, color, date, select, radio, true_false | the stored value, as a string; a textarea keeps its newline and gets no `<br>`; a date honours ACF's `return_format` | select/radio: `__label` **only when ACF's return format is `array`** - with the default `value` format the label variable is not registered (measured empty) |
| image, file | the URL, whatever ACF's return format says (`array` and `id` both rendered the URL) | `__id` |
| link (ACF, array) | the URL | `__title`, `__target` |
| page_link | the permalink | - |
| post_object (ACF) | **the ID** | `__label` = title, `__url` = permalink |
| post (Meta Box) | **the title** | `__id`, `__url` - the two providers put opposite things in the primary slot |
| user (ACF) | the ID | `__label` = display name, `__url` = author archive |
| user (Meta Box) | the display name | `__id`, `__url` |
| oembed | the `<iframe>` HTML - **but see below** | Meta Box adds `__url`, the source URL |
| wysiwyg | the HTML; Meta Box's arrives wrapped in Mosaic's own `wp-site-blocks` / `entry-content` divs because its value runs through `the_content` | - |
| checkbox (ACF), checkbox_list (Meta Box), relationship, taxonomy, image_advanced, file_advanced, post (multiple), cloneable | a loop | rows: `value` (ACF reference rows: the ID; Meta Box: the title / URL), `value__label`, `value__url`, `value__id`, `index` |
| group (ACF) | a loop of one row, named `loop-k` | `value_<sub>` per sub-field |

## Inline access to a loop

`@LOOP` takes `(loop, index, row-variable)` pairs and works inside a text node
without a loop element:

```
@LOOP('post/loopacf_rel', 1, 'value__label')   ->  Sample Page        row 1 (1-based)
@LOOP('post/loopacf_rel', 0, 'value__label')   ->  Sample Page, Shop  index 0 = every row, joined ", "
@LOOP('post/loop-acf_group', 1, 'value_ga')     ->  group text
```

A **loop element** is the real thing: `loop > loop-items > loop-item > …`, with
the source on the loop node:

```json
{"type": "loop",
 "data": {"loopType": "localContext",
          "localContextOptions": {"loopSource": {"v": "@LOOP('post/loopacf_rel')"}}},
 "children": [{"type": "loop-items", "children": [{"type": "loop-item", "children": [
   {"type": "text", "data": {"tagName": "p"},
    "children": [{"type": "wysiwyg-variable", "data": {"dynamicCode": "@VAR('item/value__label')"}}]}
 ]}]}]}
```

`loopType:"localContext"` is the built-in source that evaluates an expression in the
page's context; the sweep's `loop` COMMIT_500 is what happens without it. The loop
rendered exactly the rows the field holds for every family above (2, 2, 1, 1, 2, 2,
2 rows), and an empty field renders `m-loop--no-result` with the `loop-no-result`
child rather than nothing.

## The three empties, explained

- `@VAR('post/meta_acf_select__label')` with ACF's default `value` return format: the
  handler registers `__label` only for `return_format: array`. Switch the field or
  use `@VAR('post/meta_k')` and map it yourself.
- **oEmbed inside a text node is empty**, with `@VAR` and with `@VAR_RAW` alike - the
  wysiwyg text pipeline strips the `<iframe>`. Put it in a `code` node instead:
  `<div>@VAR_RAW('post/meta_acf_oembed')</div>` delivered the full YouTube iframe.
  The same route carries Meta Box's wysiwyg HTML intact.

## What did not need a field plugin

`meta_footnotes` appeared in the list on a page with neither ACF nor Meta Box
registering it: every non-underscore `post_meta` key present on the post type is
exposed as `meta_<key>` (`MetaFieldUnknown`, a plain string). A site that stores
its data with `update_post_meta()` and nothing else is already readable.
