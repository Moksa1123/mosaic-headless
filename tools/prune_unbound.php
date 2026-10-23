<?php
/**
 * Remove the templates and masters no post is bound to, and the nodes under them.
 *
 *   wp eval-file prune_unbound.php <themeID>            # dry run: counts only
 *   wp eval-file prune_unbound.php <themeID> --apply    # delete
 *
 * Every build_site.py / build_page.py run makes a fresh master and template and
 * re-binds the post to them; the previous pair stays behind, bound to nothing.
 * On the test theme that grew to 1,028 templates and 440k nodes with 75 templates
 * actually in use, and Mosaic's own ZIP export of a theme that size dies at the
 * nginx timeout. There is no REST route that deletes a template, so this is SQL.
 *
 * What is KEPT, in one theme only:
 *   - every template a row of wp_mosaic_template_assigns points at
 *   - every template with assign="auto" (fallbacks, condition-matched templates,
 *     the sweep's own Sweep Home) - they are bound by conditions, not assigns
 *   - every master a kept template uses
 * Everything else of type template / master goes, with its nodes. Then nodes whose
 * parent node no longer exists are removed pass after pass until none are left,
 * because each pass orphans the next level down.
 *
 * Back up first - this has no undo:
 *   wp db export pre-prune.sql --tables=$(wp db tables "wp_mosaic_*" --all-tables --format=csv)
 * (`wp db tables` without --all-tables finds no wp_mosaic_* tables: they are not
 * registered with $wpdb.) Purge the page cache afterwards and fetch every bound page.
 */
$args  = isset($args) ? $args : [];
$id    = isset($args[0]) ? trim($args[0]) : '';
$apply = in_array('--apply', $args, true);

if (!preg_match('/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i', $id)) {
    WP_CLI::error('usage: wp eval-file prune_unbound.php <themeID> [--apply]');
}

global $wpdb;
$p = $wpdb->prefix;
if (!$wpdb->get_var($wpdb->prepare("SELECT ID FROM {$p}mosaic_themes WHERE ID = %s", $id))) {
    WP_CLI::error("no theme $id");
}

$unboundTemplates = $wpdb->get_col($wpdb->prepare(
    "SELECT t.ID FROM {$p}mosaic_templates t
      WHERE t.themeID = %s AND t.assign <> 'auto'
        AND t.ID NOT IN (SELECT parentID FROM {$p}mosaic_template_assigns WHERE parentType = 'template')",
    $id));
$unusedMasters = $wpdb->get_col($wpdb->prepare(
    "SELECT m.ID FROM {$p}mosaic_masters m
      WHERE m.themeID = %s
        AND m.ID NOT IN (SELECT masterID FROM {$p}mosaic_templates
                          WHERE themeID = %s AND (assign = 'auto'
                             OR ID IN (SELECT parentID FROM {$p}mosaic_template_assigns WHERE parentType = 'template')))",
    $id, $id));

$count = function ($type, $ids) use ($wpdb, $p, $id) {
    $n = 0;
    foreach (array_chunk($ids, 500) as $chunk) {
        $in = implode(',', array_fill(0, count($chunk), '%s'));
        $n += (int)$wpdb->get_var($wpdb->prepare(
            "SELECT COUNT(*) FROM {$p}mosaic_nodes WHERE themeID = %s AND documentType = %s AND documentID IN ($in)",
            array_merge([$id, $type], $chunk)));
    }
    return $n;
};

$kept = (int)$wpdb->get_var($wpdb->prepare("SELECT COUNT(*) FROM {$p}mosaic_templates WHERE themeID = %s", $id))
    - count($unboundTemplates);
WP_CLI::log(sprintf('templates: %d unbound, %d kept', count($unboundTemplates), $kept));
WP_CLI::log(sprintf('masters:   %d unused', count($unusedMasters)));
WP_CLI::log(sprintf('nodes:     %d under those templates, %d under those masters',
    $count('template', $unboundTemplates), $count('master', $unusedMasters)));

if (!$apply) {
    $orphans = (int)$wpdb->get_var($wpdb->prepare(
        "SELECT COUNT(*) FROM {$p}mosaic_nodes n LEFT JOIN {$p}mosaic_nodes q ON q.ID = n.parentID
          WHERE n.themeID = %s AND n.parentType = 'node' AND q.ID IS NULL", $id));
    WP_CLI::log("orphan nodes already present: $orphans");
    WP_CLI::success('dry run - nothing deleted. Back up, then re-run with --apply');
    return;
}

$delete = function ($table, $type, $ids) use ($wpdb, $p, $id) {
    $nodes = $rows = 0;
    foreach (array_chunk($ids, 500) as $chunk) {
        $in = implode(',', array_fill(0, count($chunk), '%s'));
        $nodes += (int)$wpdb->query($wpdb->prepare(
            "DELETE FROM {$p}mosaic_nodes WHERE themeID = %s AND documentType = %s AND documentID IN ($in)",
            array_merge([$id, $type], $chunk)));
        $rows += (int)$wpdb->query($wpdb->prepare(
            "DELETE FROM {$p}mosaic_{$table} WHERE themeID = %s AND ID IN ($in)",
            array_merge([$id], $chunk)));
    }
    return [$rows, $nodes];
};

// nodes first, so a failure part-way never leaves a document row with half its tree
[$t, $tn] = $delete('templates', 'template', $unboundTemplates);
[$m, $mn] = $delete('masters', 'master', $unusedMasters);

$orphans = 0;
do {
    // MariaDB cannot DELETE from a table it is also reading in a subquery; a JOIN it can
    $n = (int)$wpdb->query($wpdb->prepare(
        "DELETE n FROM {$p}mosaic_nodes n LEFT JOIN {$p}mosaic_nodes q ON q.ID = n.parentID
          WHERE n.themeID = %s AND n.parentType = 'node' AND q.ID IS NULL", $id));
    $orphans += $n;
} while ($n > 0);

$dangling = (int)$wpdb->get_var($wpdb->prepare(
    "SELECT COUNT(*) FROM {$p}mosaic_templates t LEFT JOIN {$p}mosaic_masters m ON m.ID = t.masterID
      WHERE t.themeID = %s AND m.ID IS NULL", $id));
WP_CLI::log("deleted: $t templates ($tn nodes), $m masters ($mn nodes), $orphans orphan nodes");
if ($dangling) {
    WP_CLI::error("$dangling kept templates point at a master that is gone - restore the backup");
}
WP_CLI::success('pruned. Purge the page cache and fetch every bound page');
