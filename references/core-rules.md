# Core rules: look it up, check the page, build native

Moved out of SKILL.md on 2026-11-16 (skill SOP pass). SKILL.md keeps the routing; the reasoning and the failure-mode table live here.

## The one rule that overrides everything

**Never write a node type, property name, enum value, style key or Free/Pro claim
from memory. Look it up in `data/`.**

And look it up with `mo.py`, not with grep. Grep answers the question you typed;
it does not answer the question you have. Ask grep about `accordion-content` and it
confirms the type exists. The sweep table says BROKE_PAGE: place one and the entire
public page becomes a 54-byte error string. Both are true, and both are the wrong
answer - the note beside the row says the string is `AccordionItemElementMResource
instance required`, that this is a type committed without the parent its factory
needs, and that nested under `accordion > accordion-item` it commits, renders and
gives you a keyboard-operable disclosure for free. `mo.py type` shows all three in
one answer. Grep shows one, the CSV shows two, and the skill was itself wrong about
this type for a week.

```bash
python tools/mo.py stats                    # the surface, and what is unsafe
python tools/mo.py type accordion-content   # ONE type, joined to every sweep
python tools/mo.py params text              # EVERYTHING settable on a type:
                                            # data properties, the states that
                                            # reach it, the style surface, placement
python tools/mo.py types --edition pro --safe
python tools/mo.py check div text button    # exits 1 on an unsafe or unknown type
python tools/mo.py placement accordion-item # what goes inside what, both directions
python tools/mo.py prop tagName             # one node property + how it was probed
python tools/mo.py props --shared           # the ones every element carries
python tools/mo.py style --grouped          # the 20 that are inert set on their own
python tools/mo.py css border-radius        # which Mosaic key drives this CSS
python tools/mo.py states --grep hover      # state IDs and their selector templates
python tools/mo.py states --verified        # only the ones measured to compile
python tools/mo.py vars --namespace post    # the @VAR() surface
python tools/mo.py classes --grep Heading   # variants: the theme-global element classes
python tools/mo.py routes --grep template
python tools/mo.py tables wp_mosaic_nodes
python tools/mo.py skeleton                 # a minimal valid page spec
```

`--json` on any of them for machine-readable output. Every answer leads with the
measured verdict rather than the declaration, because on this platform the two
disagree for 52 of the 122 types they were first counted on.

Then check the page. Mosaic has eight failure modes and **only three of them change the
HTTP status code**:

```
clean validator rejection   HTTP 200  + an `exceptions` array in the body
PHP fatal during commit     HTTP 500  (15 of 129 types do this from a plain div)
structurally invalid node   HTTP 200, committed, row in the DB, and the whole
                            public page becomes a 54-byte error string
wrong value SHAPE           HTTP 200, stored, and the CSS rule is simply absent -
                            or worse, compiles to `transform:none`
right rule, wrong result    HTTP 200, in the stylesheet, correct, and the BROWSER
                            computes something else: a unit that resolves against
                            something you forgot, a font that cannot render the
                            text, a property the layout mode overrides
no template for the URL     HTTP 406 with an EMPTY BODY for anyone not logged in
render-time fatal from      HTTP 500 - the commit went through and the page dies
CONTENT                     when Mosaic parses it. A `code` node's content is a
                            template: `@media(` (as every minifier writes it) is
                            read as a function call and kills the whole page.
                            `@media (` renders. build_page refuses the former.
plugin upgrade renamed      HTTP 200, page intact, rows migrated - and a selector
what the page emits         you wrote against an emitted class matches nothing.
                            1.0.8: `M_EL4 M_EL_Div` -> `m-div _e`, the state
                            classes with them, `customStyles` -> `customDeclarations`.
                            The worked example's tap-to-enlarge stopped opening
                            and only `verify_loop.py` OPENS said so.
```

That last one also fooled every checker here for a day: WordPress answers a fatal
with a 2,697-byte error document, which is larger than the 2,000-byte "healthy"
floor, and `Client.page()` returned that body as if it were the page - so
`build_site` printed `OK 2645 bytes` over an HTTP 500. A 5xx now reads as an
empty page, which is what it is.

**406 is Mosaic's "no template matched".** `FrontendRenderer` answers
`TemplateNotFoundException` with `status_header(406)` and prints the explanation
only for an admin, so a logged-out visitor gets a blank page and a status code
that looks like a server problem. Two things make it easy to hit:

- **There are TWO ways to bind a template, and `createManualTemplate` is only one
  of them.** That endpoint takes `resourceQuery=post/<id>` and `post` is the only
  resource type it registers (`setResourceType('post')`, three call sites), so
  through it there is no catch-all. But `assign` and `path` are first-class columns
  on `wp_mosaic_templates`, and a template row committed with `assign:"auto"` and
  `path:"index.php"` binds to a template PATH instead of a post. Measured A/B on a
  URL with no template of its own: 406 with no such row, handled with it, 406 again
  after deleting it. `X-Mosaic-Paths` on any 406 names the paths Mosaic looked for,
  and `index.php` is in every list.

  This `index.php` row is the editor's **Fallback → Empty** template: priority
  `PHP_INT_MAX`, matching every request (`Plugins/Paths/PathIndex.php`). Since 1.0.10
  an auto template is an ordinary writable one - it is listed by
  `adminTemplateEditorInstance` and its document carries a `template-internal`
  root, so content goes in like any page's (the commit shape is in
  `references/templates-and-conditions.md`). Before 1.0.10 both were missing and a
  direct commit answered HTTP 500.

  For `/` specifically the WordPress-side fix is the sound one: point the front page
  at a post that has a template (`show_on_front=page`, `page_on_front=<id>`).
- **Activating a theme is not the same as populating it.** A fresh theme has no
  templates, so between `wp theme activate` and a successful build the whole site
  is 406 - and if the build fails, it stays that way. Never activate a new theme
  as a step that can be separated from the commit that fills it.

A successful commit is not evidence of a working page, and neither is a correct
stylesheet. Fetch the page and check its size; then run `verify_browser.py` and let
the element say what it actually got. `references/failure-modes.md` has all of them,
measured.

## Native first: what the client can open in the editor

The second rule, and the one an agent breaks most often: **build with Mosaic's own
features, not with code.** A `code` node, a `script` action, or a pile of
`customDeclarations` renders fine and is a dead end for the client - the editor
shows a box of text they cannot change, the Navigator shows nothing of its
structure, and the next agent has to reverse-engineer it. Mosaic's tutorials build
every one of the effects below with no custom code; this skill can now write all of
them headlessly, measured.

| the job | the native way | how, headlessly |
|---|---|---|
| dark / light mode, themed sections | a second mode on the colour collection; `collectionModesData` on a band, or the Variable modes action on `document` for the whole site | references/design-system.md (modes), the switcher recipe in references/interactions.md |
| any animation: reveal, fade, slide, loop, parallax | an interaction (`pageLoad`, `click`, `hover`, `elementScrollIntoView`, `scrollIntoView`...) | `tools/interactions.py`; never `@keyframes` in a code node |
| the same animation on many elements | a universal class as the interaction's trigger, empty target | `trigger=class_target(...)`, recipe in references/interactions.md |
| a hover / focus look with no motion sequence | a style state (`hover`, `focus`...) with a `transition` | references/styling.md |
| a loading screen, a cookie bar | a fixed div + `pageLoad` + `hide_at_end`, `data.hidden: true` so it does not block editing | recipe in references/interactions.md |
| a block repeated on several pages | a component, one definition, overrides per instance | references/design-system.md (components) |
| a popup, a drawer, a tour | the `modal` / `popover` nodes and their actions | references/dialog-and-triggers.md |
| a site menu: desktop hover dropdown + phone drawer | `dropdown` / `dropdown-wide` with `openOn: hover`; a `modal` drawer opened by `modalOpen` (there is no off-canvas node) | references/design-system.md (site menus), `tools/verify_menus.py` |
| a typeface, site-wide | a `fontFamily` collection variable, `{"var": id}` in styles; Settings: `saveGoogleFontsLocally` on and `fontDisplay: swap` (unset is `block`) | references/styling.md (fonts) - saving Google fonts locally took a CJK page from 68 to 96 on mobile |
| remembering a visitor's choice | `setCookie`, `remember` / `forget`, cookie conditions | references/interactions.md |
| text that comes from the post, the user, a field | a dynamic `{"v": "@VAR(...)"}` value | references/dynamic-content.md |
| a colour, a size used twice | a collection variable | references/design-system.md |

Reach for custom code only when no row above fits and `mo.py` finds no node,
property or action for the job - and then say in the spec, next to the code, which
native path was checked and why it falls short.
