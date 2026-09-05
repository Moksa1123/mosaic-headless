# The Mosaic data model

## Where a page lives

Nowhere you would guess from Elementor or Gutenberg. Mosaic stores **nothing** of a
page's structure in `wp_posts` or `wp_postmeta`. It owns **23 of its own tables**,
all prefixed `wp_mosaic_`, and the WordPress post is only one of several things a
Mosaic *template* can be assigned to.

Measured on a real install (`data/db-columns.csv`, 23 tables / 206 columns):

| table | holds |
|---|---|
| `mosaic_themes` | the top-level container. Everything else is scoped to a `themeID`. |
| `mosaic_masters` | master layouts (the outermost shell a template renders into) |
| `mosaic_templates` | a template + its `conditions` blob and `path`/`assign` mode |
| `mosaic_template_assigns` | which template serves which `type`/`typeIdentifier` |
| `mosaic_nodes` | **the element tree** — one row per element, on every document |
| `mosaic_components`, `mosaic_component_documents`, `mosaic_component_categories` | reusable components and their category tree |
| `mosaic_styleguides` | style guide documents |
| `mosaic_element_classes`, `mosaic_sub_classes` | the built-in class system (151 classes, see `data/element-classes.csv`) |
| `mosaic_utility_classes`, `mosaic_utility_sub_classes` | user-defined utility classes |
| `mosaic_collections`, `mosaic_collection_modes`, `mosaic_collection_skins`, `mosaic_collection_groups`, `mosaic_collection_variables` | the design-token system (a collection has modes and skins; variables resolve per mode) |
| `mosaic_breakpoints` | responsive breakpoints, per theme — not global |
| `mosaic_settings` | theme-scoped settings |
| `mosaic_submissions`, `mosaic_submission_actions` | form submissions (Pro) |
| `mosaic_locks` | editing locks; the only table created at plugin activation |

`mosaic_locks` appearing alone is the signature of a **half-installed** Mosaic: the
plugin's network-level install ran, but the site-level install (which creates the
other 22 tables) has not. It is triggered by an admin loading
`/wp-admin/admin.php?page=mosaic`, not by activation.

## The node row

`mosaic_nodes` is the whole element tree, flattened:

```
themeID       varchar(36)   scope
documentType  varchar(36)   which kind of document this node belongs to
documentID    varchar(36)   which document
ID            varchar(36)   node uuid
parentType    varchar(36)   parent's kind
parentID      varchar(36)   parent node uuid   -> the tree lives here
ordering      varchar(400)  fractional-index string, NOT an integer
status        varchar(36)   'publish' etc.
type          varchar(128)  the node type slug -> data/node-types.csv
data          longtext      the node's own properties, JSON
revision      varchar(36)   optimistic-lock token
version       varchar(128)
```

Two things bite here:

**`ordering` is a string, not a number.** It is a fractional index (`a0`, `a1`,
`a0V`…), so siblings sort lexicographically and a node can be inserted between two
others without renumbering. Sorting it numerically produces a scrambled page.

**The tree is by `parentID`, not by nesting.** There is no nested JSON blob to edit
like `_elementor_data`. Reparenting is a single-column update; moving a subtree
does not touch the subtree's rows.

## Node types and properties

122 node types are registered (`data/node-types.csv`), **48 of them Pro-only** —
the split is structural, not a flag: Pro types live under `Mosaic/NodeTypes/Pro/`
and cover the whole form system, slider, tabs and code element. If a type's
`edition` column says `pro`, a Free install has no factory for it and the node
falls back to the `__unknown` type rather than erroring.

Each type declares its own data properties (`data/node-properties.csv`, 181
properties across 49 classes). Properties are declared by `createDataSimple` (175),
`createDataArray` (3) and `createDataGroup` (3), each with a validator chain. **174
of 181 properties set `supportsInherit: true`** — inheritance is the norm in this
model, not the exception, which is why a property being absent from a node's `data`
is meaningful rather than merely missing.

The validator chain in the `validators` column is what actually gates a write.
`ValidatorAcceptedValues` means an enum (the accepted list is in the source file
named by the `file` column); `ValidateAllowUndefined` means the property may be
omitted; `ValidatorDynamicCodeObject` means the property accepts a dynamic-code
object instead of a literal — that is Mosaic's dynamic-tag equivalent.

## Styling

Mosaic does not attach CSS to a node the way Elementor attaches controls to a
widget. Styling goes through the **element class** system: 151 built-in classes
(`data/element-classes.csv`), each with its own CSS selectors, arranged in a parent
tree, some marked `metaIsGroup` (organisational) and some `metaIsEditable`. A node
points at a default element class (`default_element_class` in `node-types.csv`) and
takes variations from there.

That is why the same visual change can be made in two very different places, and
why writing a style onto a node directly is usually the wrong move: the class is
the unit of reuse, and the collection/variable tables are the token layer beneath it.
