---
max_turns: 20
allowed_tools: [Read, Glob, Grep, Skill]
---

I committed a Mosaic `code` node containing a minified stylesheet - the commit
returned HTTP 200 with every revision accepted - and now the whole public page
returns HTTP 500 with WordPress's "critical error" screen. The stylesheet starts
with `<style>.hero{color:#fff}@media(max-width:767px){.hero{font-size:24px}}</style>`.
The commit looks fine. What is wrong and how do I fix it?
