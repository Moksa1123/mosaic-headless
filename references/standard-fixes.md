# Standard fixes and procedures

Problems that came back on real Mosaic sites until they were fixed the same way each
time. Each one names its check; run the check before and after, and report the result,
not the intent. Measured on a Mosaic 1.0.13 + WooCommerce 11.3 store (2026-11-21):
every check failed before its fix and passed after.

## The product-image lightbox: close button not in the corner

**Symptom.** Zoom a product image on a phone, tablet or small laptop and the close
button sits 44px in from the top-right corner.

**Cause.** WooCommerce's `photoswipe/default-skin.min.css` makes `.pswp__preloader`
`position: relative` and `float: right` at 1024px and narrower, so the loading spinner
takes the right-most 44px of the toolbar. It is WooCommerce's CSS, not Mosaic's, so
every Mosaic + WooCommerce site has it.

**Fix** (site CSS, after WooCommerce's):

```css
.pswp .pswp__top-bar .pswp__preloader{position:absolute;left:50%;top:0;margin-left:-22px;float:none}
```

**Check.** `python tools/verify_lightbox.py --url <a product page>`: at 390, 820, 1024
and 1440px the close button is flush with the toolbar's top-right corner, the counter
with its top-left, and the spinner is out of the flow. Exit 1 on any FAIL.

## A sticky column that rides over the content below

**Symptom.** The product summary (or any sticky column) follows the reader down and
covers the tabs, the description or the related products.

**Cause.** `position: sticky` sticks within its parent. When the parent is the whole
product block, the column's range is the whole page section. `getComputedStyle` says
`sticky` throughout, so a check that only reads the computed position passes a page
that is plainly broken.

**Fix.** Give the sticky column a parent that holds only what it should travel beside:
on WooCommerce, wrap the gallery and the summary in their own container (through the
`woocommerce_before_single_product_summary` / `woocommerce_after_single_product_summary`
hooks, or a Mosaic `div` around the two), and make that container the sticky range.

**Check.** `python tools/verify_sticky.py --url <page> --sticky <column> --bound
<its container> --avoid <tabs> --avoid <related> --top <offset>`: it scrolls in steps
and measures rectangles at every step - no intersection with an `--avoid` element,
never past the bottom of `--bound`, and actually stuck at `--top` while the container
is on screen. Exit 1 on any FAIL.

## Rebuilding a template: never clear it first

**Symptom.** A template is cleared (its children deleted), the rebuild then fails -
on that site with `style references token '--x' before it is declared in
theme.variables` - and the page it serves is blank until someone notices (8 minutes
there).

**Procedure.**

1. Convert and validate the whole new tree first. `build_page.py` refuses a bad spec
   before it commits the page's nodes (it has already created a new, empty master by
   then, which `prune_unbound.php` clears later; the old template is untouched). A
   token the spec uses must be declared in its `theme` block or already exist in the
   theme.
2. Only after the new tree validates, replace the old nodes - in one commit where the
   tool allows it, otherwise build the new tree first and delete the old one last.
3. Check the delivered page (`verify_rwd.py` / `verify_browser.py`, or at least an HTTP
   200 with Mosaic markup and its expected size).

**Tokens from the master.** A template that styles with the master theme's tokens
needs their ids before it is built: `build_page.theme_records()` loads them into
`VAR_IDS`. It also writes the theme's collection variables again, so a site with a
second mode (dark mode) must re-apply that mode's values afterwards
([design-system.md](design-system.md), modes), and re-check them with
`verify_tokens.py`.

## Before deleting a root or rebuilding a component

See [facts.md](facts.md), "Changing a component's roots or its node ids empties its
instances' overrides everywhere else": back up `wp_mosaic_nodes`, export the
instances' override nodes, change, render, then run `tools/override_health.sql`.
