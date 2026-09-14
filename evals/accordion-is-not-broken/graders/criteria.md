---
type: llm
weight: 1
---

The right answer corrects the premise using what the skill measured: the sweep
committed every type alone under a plain div, and accordion-item / accordion-content
broke there because they were committed WITHOUT the parent their factory requires
(the error strings name the missing parent). Nested properly -
accordion > accordion-item > (accordion-title, accordion-content) - they commit,
render as <dl><div class=M_EL_AccordionItem><dt tabindex=0 aria-expanded><dd>, and
give keyboard operation and a screen-reader state for free.

Score highly when the answer:
1. Says the accordion IS usable and explains the BROKE_PAGE row as a parent artefact
   of the sweep method, not a verdict on the type.
2. Gives the correct nesting, with accordion-title and accordion-content under
   accordion-item.
3. Recommends the native accordion over hand-rolled divs for an FAQ, ideally
   mentioning the accessibility it provides (tabindex/aria-expanded) or that
   tools/probe_accordion.py proved it.

Score 0.5 if it recommends the native accordion but does not explain the nesting or
why the table says BROKE_PAGE. Score 0 if it agrees the accordion should be avoided.
