# Mosaic + WooCommerce: the standard kit and checklist

> Directory edition: commands that mention `tools/` need the full edition (`npm` package `mosaic-headless`); this folder ships reference files only. The `wp` commands run on your WordPress host; how you reach it is up to you.

What a WooCommerce store built on Mosaic needs beyond the pages themselves. Collected
from a live store's conversion (Mosaic 1.0.13, WooCommerce 11.3, 2026-11-20/21):
each item failed there before its fix and passed after. Snippets marked *(that
site)* are that site's fix, not re-run here; adapt them to your theme's own hooks.
WooCommerce and WordPress hooks named here are their public APIs.

## Why: WooCommerce treats Mosaic like a block theme

Mosaic renders the page itself, so WooCommerce takes the block-theme path and leaves
out pieces a classic theme would get. Four symptoms follow:

1. **No gallery zoom, lightbox or slider.** Declare them:

   ```php
   add_action('after_setup_theme', function () {
       add_theme_support('wc-product-gallery-zoom');
       add_theme_support('wc-product-gallery-lightbox');
       add_theme_support('wc-product-gallery-slider');
   });
   ```

2. **`wc-single-product` is dequeued** by WooCommerce's block-template controller
   (`dequeue_legacy_scripts`, priority 20), so the gallery and tabs do nothing.
   Enqueue it again later:

   ```php
   add_action('wp_enqueue_scripts', function () {
       if (function_exists('is_product') && is_product()) {
           wp_enqueue_script('wc-single-product');
       }
   }, 30);
   ```

3. **Block-style notices take focus.** WooCommerce moves focus to
   `.wc-block-components-notice-banner`, which then shows a focus ring on a box that
   is not a control, and its "View cart" link arrives unstyled. *(that site)* Drop
   the ring for programmatic focus only - keep it for keyboard users - and style the
   link:

   ```css
   .wc-block-components-notice-banner:focus:not(:focus-visible){outline:none}
   ```

4. **The gallery jumps as it loads** (a phone CLS of 0.27 there). *(that site)*
   Reserve the thumbnail row's height before the slider initialises - a container
   query on the gallery sizes the row from the gallery's own width - and re-measure
   with a CLS check.

## The product page

| Item | Fix | Check |
|---|---|---|
| Lightbox close button not in the corner (WooCommerce's skin, 1024px and below) | the one-line preloader rule in [standard-fixes.md](standard-fixes.md) | `tools/verify_lightbox.py --url <product>` exit 0 |
| Sticky summary riding over the tabs and related products | give it its own container ([standard-fixes.md](standard-fixes.md)) | `tools/verify_sticky.py` exit 0 |
| Gallery script missing | item 2 above | the gallery slides and zooms |

## Archives

- **"Category:" in front of every archive title** comes from WordPress's
  `get_the_archive_title()` prefix. On a Mosaic site:

  ```php
  add_filter('get_the_archive_title_prefix', '__return_empty_string');
  ```

## A site converted from Elementor

*(that site)* Two leftovers keep running after the pages are Mosaic:

- **Elementor Pro popups still print** on Mosaic pages (its popup module prints them
  in the footer). Remove that output on Mosaic-rendered pages, or retire the popups
  and rebuild them as Mosaic `modal` / `popover` nodes
  ([dialog-and-triggers.md](dialog-and-triggers.md)).
- **`elementor-frontend` still loads** on pages that have no Elementor content, and
  logs errors to the console. Dequeue its script and style where the page has no
  Elementor data.

## Phones

- **Tap targets of at least 40×40px** (WCAG's AAA level asks 44). An icon-only
  header button was 28px wide there: give icon buttons a `minWidth` / `minHeight`
  of 44px in the phone breakpoint. `tools/audit_mobile.py` reports `SMALL_TARGET`
  below `--min-target` (40 by default).
- **Test touch with real touch events.** A script that dispatches
  `new TouchEvent(...)` in the page is ignored by WooCommerce's FlexSlider, so a
  working phone gallery looks broken. Use the browser's own input: a Playwright
  context with `has_touch=True` and `page.tap()` / `page.touchscreen.tap()`, or the
  DevTools protocol's `Input.dispatchTouchEvent`. This skill's verifiers already do
  (`verify_menus.py` taps on touch contexts; none synthesises a `TouchEvent`).

## Speed

Mosaic has no page-output cache, and rendering time grows with the node count
([facts.md](facts.md), second site). A WooCommerce store on Mosaic needs a full-page
cache in front of it (with cart, checkout and account excluded), and a header and
footer kept lean.

## Checklist

| # | Check | How |
|---|---|---|
| 1 | Gallery zoom, lightbox and slider declared | theme support, item 1 |
| 2 | `wc-single-product` loaded on product pages | item 2; the gallery slides |
| 3 | Notice focus ring and "View cart" link | item 3 |
| 4 | Gallery does not shift while loading | item 4; a CLS measurement |
| 5 | Lightbox toolbar | `verify_lightbox.py` exit 0 |
| 6 | Sticky summary | `verify_sticky.py` exit 0 |
| 7 | Archive titles without a prefix | the filter above |
| 8 | No Elementor leftovers on converted sites | page source: no popup markup, no `elementor-frontend` where unused |
| 9 | Tap targets on phones | `audit_mobile.py --min-target 40` reports no `SMALL_TARGET` |
| 10 | Full-page cache on, cart / checkout / account excluded | response headers on a repeat fetch |
