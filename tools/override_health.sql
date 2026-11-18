-- override_health.sql - read only. Component instances whose override nodes were emptied.
--
--   wp db query < tools/override_health.sql
--
-- An instance (a node whose type starts with component-instance/) owns one override node
-- per node of its component: parentType 'override', parentID = the instance, and
-- data.override.originalID = the component node it shadows. A SHELL is an override node
-- whose data is nothing but {"override":{"originalID":...}}: no text, no url, no attrID.
-- build_site.py writes an attrID into every override node, so on a site built by this
-- skill a shell means heal rebuilt the node and dropped its content. Measured on a live
-- site (2026-11-17): deleting a component's extra empty root made the next front-end
-- render's heal turn every override of that component's instances in the master into a
-- shell, and the header and footer lost all their text and links.
--
-- Result 1: per instance, how many override nodes and how many are shells.
--   all_shells = 1 is the failure signature. Some shells on an instance whose component
--   has nodes with nothing to override can be normal on a hand-built site; compare with
--   the export taken before the change.
-- Result 2: duplicate override nodes (the same instance shadowing the same component
--   node twice).
SELECT LEFT(o.themeID, 8) AS theme, o.documentType, LEFT(o.documentID, 8) AS doc,
       LEFT(o.parentID, 8) AS instance, i.type AS instance_type,
       COUNT(*) AS overrides,
       SUM(JSON_LENGTH(o.data) = 1 AND JSON_LENGTH(o.data, '$.override') = 1
           AND JSON_CONTAINS_PATH(o.data, 'one', '$.override.originalID')) AS shells,
       SUM(JSON_LENGTH(o.data) = 1 AND JSON_LENGTH(o.data, '$.override') = 1
           AND JSON_CONTAINS_PATH(o.data, 'one', '$.override.originalID')) = COUNT(*) AS all_shells
  FROM wp_mosaic_nodes o
  LEFT JOIN wp_mosaic_nodes i ON i.ID = o.parentID AND i.themeID = o.themeID
 WHERE o.parentType = 'override' AND JSON_VALID(o.data)
 GROUP BY o.themeID, o.documentType, o.documentID, o.parentID, i.type
HAVING shells > 0
 ORDER BY all_shells DESC, shells DESC;

SELECT LEFT(themeID, 8) AS theme, LEFT(parentID, 8) AS instance,
       JSON_UNQUOTE(JSON_EXTRACT(data, '$.override.originalID')) AS original, COUNT(*) AS n
  FROM wp_mosaic_nodes
 WHERE parentType = 'override' AND JSON_VALID(data)
 GROUP BY themeID, parentID, original
HAVING n > 1;

SELECT COUNT(*) AS override_nodes, COUNT(DISTINCT parentID) AS instances
  FROM wp_mosaic_nodes WHERE parentType = 'override';
