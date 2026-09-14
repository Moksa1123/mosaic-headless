---
type: llm
weight: 1
---

The skill documents two paths and one serious trap. Score highly when the answer:

1. Names at least one real path from the skill: `theme_export.php` /
   `theme_import.php` (JSON rows over WP-CLI, ids kept because every scoped table has
   a composite (themeID, ID) primary key) and/or `theme_zip.py` driving Mosaic's own
   ZIP export/import over its milestone protocol.
2. States the trap: Mosaic's native import DEFAULTS TO ACTIVATING the imported theme
   as the live site (themeActivateMode falls back to 'live'), and `replaceThemeID`
   deletes the theme it names - so the import should be run in test mode first
   (theme_zip.py does this unless told --activate).
3. Mentions that a whole theme moves, never a single page, and/or that a tree-walking
   import drops orphan nodes that a row-copy carries.

Score 0.5 if it gives a real path but omits the live-activation trap. Score 0 if it
suggests copying the database or the theme folder by hand, or invents an
export feature that the skill does not document.
