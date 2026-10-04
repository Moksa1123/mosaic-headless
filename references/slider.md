# The slider, measured

`sweep_node_types.py` records the whole slider family as `COMMIT_500` or
`BROKE_PAGE`. That is true of a bare `slider` under a plain `div` and says nothing
about the component — the same kind of row the accordion probe corrected. Nested
the way its factories require, every piece commits and renders.

`data/slider-verification.csv`: 30 checks across two sliders, all passing.

## The shape

```json
{"type": "slider",
 "data": {"animation": "slide", "duration": "650", "easing": "ease",
          "isAutoplay": "1", "autoplayDelay": "2200", "autoplayLimit": "0",
          "isCarousel": "0", "defaultSlideIndex": "0", "ariaLabel": "…"},
 "children": [
   {"type": "slider-slides", "children": [
       {"type": "slider-slide",
        "data": {"image": "wp-attachment://image/5/full/…", "useAsBackground": "1",
                 "alt": "…", "title": "ONE", "positionX": "50%", "positionY": "50%"},
        "children": [ … the caption, which rides inside the slide … ]},
       …]},
   {"type": "slider-navigation", "children": [
       {"type": "slider-navigation-bullet"}]},        // ONE - see below
   {"type": "slider-arrow-left"},
   {"type": "slider-arrow-right"}]}
```

`animation` is `slide` | `crossFade` | `fadeOut` | `fadeOver`. `autoplayLimit` is how
many rounds autoplay runs before it stops, `0` meaning no limit.

**`isCarousel` makes the ends wrap. It does not show more than one slide at a
time** — an earlier version of this page claimed both, and measuring the two side
by side says otherwise. `<mosaic-slider-slides>` is a CSS grid whose template is a
single `"slide"` area one track wide, and *every* slide sits in that one area at
the full track width, carousel or not:

| | plain | carousel |
|---|---|---|
| `grid-template-areas` | `"slide"` | `"slide"` |
| `grid-template-columns` | `1240px` | `1240px` |
| every slide's width | 1240 | 1240 |
| first slide's `left` | 80 (the track's own left) | **−947** — one has already wrapped round |

So the only structural difference is that a carousel keeps a slide positioned
before the first one, which is both why it wraps and why neither arrow ever hides.
Showing several slides at once is not something this property gives you.

## Two things the markup does not announce

**A `slider-navigation-bullet` is a TEMPLATE.** You author one; Mosaic repeats it
once per slide. Every copy carries the **same id** — three `id="sl-dot-0"` in one
document — and only the `aria-label` differs, which Mosaic takes from each slide's
own `title`. Author three bullets and you get three templates. So address a bullet
by position inside `mosaic-slider-navigation`, never by attrID, and do not expect
the id to identify one.

**An arrow hides itself at the end it cannot pass.** `Slider.js` adds
`m-slider-arrow--hidden` when the index is 0 (prev) or the last (next), unless the
slider is a carousel. Autoplay on a non-carousel parks the slider on the last slide,
so by the time a test reaches for `next` it is legitimately gone — go back to the
first slide before asking an arrow to move anything. The hidden state is a real
style state (`___arrow_hidden` in `data/style-states.csv`), so it can be styled.

A slide's own `attrID` lands on the inner `.m-slide-content`, not on the
`<mosaic-slider-slide>` host, and a slide using its image as a background puts an
`<img>` before that div.

## What it does, measured

| | |
|---|---|
| advances | reached all 3 slides unaided at the declared 2200ms |
| arrows | `role="button" tabindex="0"` with a localised `aria-label`; next and prev each moved it |
| bullets | `role="button" tabindex="0"`, labelled from the slide titles; clicking one goes to that slide |
| keyboard | focusing a bullet and pressing Enter moves the slider — the runtime wires it, a `tabindex` alone would not |
| track | `<mosaic-slider-slides>` with `aria-live` — `off` while autoplaying, `polite` when it is not |
| reduced motion | **it holds still on its own.** Mosaic stops the autoplay; the author does not have to |

The carousel (`crossFade`, `isCarousel: "1"`, autoplay off) stayed on slide 0 for
2.6s unaided, which is the other half of the same claim: autoplay is the only thing
that moves a slider by itself.

## Verifying one

```bash
python tools/verify_slider.py --url https://site/page/ --slider sl-main \
    --autoplay 2200 --csv data/slider-verification.csv
```

Everything is addressed by position inside the slider, for the reasons above.
"Which slide is current" is what the tool reads, because `slide` and `crossFade`
drive transforms and opacities completely differently and that is the one thing
both agree on.


## Two things the component does not draw for you

**An arrow has no glyph.** `<mosaic-slider-arrow-left>` renders with empty
`innerHTML`, and its placement rule is `none`, so there is nowhere to put an icon
either. The entire appearance is the author's CSS on the element itself. The
two-border chevron works and needs nothing else: a ~9px box showing only
`border-top` and `border-right`, turned with a `rotateZ` transform entry (`45deg`
for next, `-135deg` for prev).

**`.m-slide-content` arrives as `display:flex` with `align-items: center`.** A
slide whose type should sit against the left edge has to say `alignItems:
"flex-start"`; without it every slide centres its own content and the result looks
like exactly the stock carousel you were trying not to build.

And one of layout rather than of the component: slider chrome positioned over the
slides (`position:absolute` bottom bar holding the bullets and arrows) will collide
with the slide's own text unless the slide reserves a strip of bottom padding for
it. Nothing warns you; the caption simply runs under the bullets.
