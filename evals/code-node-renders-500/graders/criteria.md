---
type: llm
weight: 1
---

The correct diagnosis is specific and measured: a `code` node's content is parsed
by Mosaic's templating parser (the one that evaluates @VAR(...) expressions), and a
CSS at-rule written WITHOUT a space before its parenthesis - `@media(` - is read as
a call to a function named `media`, whose arguments the parser cannot tokenise, so
rendering fatals (Parser::matchOperator TypeError) after a clean commit.

Score highly when the answer:
1. Names `@media(` (the glued at-rule) as the cause - not the stylesheet in general,
   not a syntax error, not a plugin conflict.
2. Gives the fix: write `@media (` with a space (or otherwise keep at-rules from
   being parsed as calls).
3. Explains why the commit succeeded anyway: the failure is at render time, not at
   validation time - Mosaic has several failure modes that never change the commit's
   HTTP status.

Score 0.5 if it correctly suspects the @ but proposes something vague (e.g. "escape
special characters"). Score 0 if it blames caching, PHP memory, the theme, or tells
the user to check error logs without identifying the cause.
