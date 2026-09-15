---
type: llm
weight: 1
---

The measured facts that decide this: Mosaic's gridColumnStart / gridColumnEnd /
gridRowStart / gridRowEnd properties exist in the style table but EMIT NOTHING (16
declarations committed, zero grid-column rules in the delivered CSS), so the
documented way to place a grid child is `customDeclarations` (`customStyles` before Mosaic 1.0.8) with a raw
`grid-column: 1 / 3;` declaration. And Mosaic's responsive axis is
states["&"][breakpoint][property] with `_` desktop, `_t` <=1079px, `_m` <=767px -
`_t` is a min/max band, so a tablet-only value goes under `_t` and, because `_m`
inherits from `_t`, must be reset under `_m`.

Score highly when the answer:
1. Does NOT recommend gridColumnStart/gridColumnEnd as the solution (or explicitly
   says they are inert and why).
2. Uses customDeclarations (or the older customStyles) with grid-column (or grid-area) for the placement.
3. Puts the value under the `_t` breakpoint and resets it under `_m` (or explains
   that breakpoints cascade downward so mobile must be handled).

Score 0.5 if it uses customDeclarations correctly but ignores the breakpoint cascade.
Score 0 if it recommends gridColumnStart or invents a breakpoint name.
