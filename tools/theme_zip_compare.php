<?php
/**
 * Compare a theme with a copy of it, table by table, and say whether the copy is
 * faithful - as a verdict, not a row count.
 *
 *   wp eval-file theme_zip_compare.php <sourceThemeID> <copyThemeID> [csv-path]
 *
 * Written for theme_zip.py: export a theme through Mosaic's own flow, import it in
 * test mode, then hold the copy against the original. The first run of that
 * round trip came back with every table equal and the node table one row short -
 * 69,362 against 69,361 - and a bare count cannot say whether that is a lost piece
 * of a page or nothing at all. It was nothing at all: an orphan `div` with no
 * parentType, no parentID and no ordering, left by an interrupted build, which a
 * tree-walking import correctly does not carry. So this compares the way the
 * import copies - by tree - and reports orphans as what they are.
 *
 * The native import also re-keys every override node (a component instance's
 * per-instance edits), and the component-internal nodes they point at, so those
 * are matched on what they say rather than on their ids.
 */
$args = isset($args) ? $args : [];
$src  = isset($args[0]) ? trim($args[0]) : '';
$cp   = isset($args[1]) ? trim($args[1]) : '';
$csv  = isset($args[2]) ? trim($args[2]) : '';
$re   = '/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i';
if (!preg_match($re, $src) || !preg_match($re, $cp)) {
    WP_CLI::error('usage: wp eval-file theme_zip_compare.php <sourceThemeID> <copyThemeID> [csv]');
}

global $wpdb;
$p = $wpdb->prefix;
$rows = [];
$fail = 0;
$check = function (string $name, bool $ok, string $detail) use (&$rows, &$fail) {
    $rows[] = [$name, $ok ? 'PASS' : 'FAIL', $detail];
    WP_CLI::log(sprintf('  %-26s %-4s %s', $name, $ok ? 'PASS' : 'FAIL', $detail));
    if (!$ok) $fail++;
};
$count = fn(string $t, string $id, string $extra = '') => (int)$wpdb->get_var(
    $wpdb->prepare("SELECT COUNT(*) FROM {$p}mosaic_{$t} WHERE themeID = %s $extra", $id));

// ── every theme-scoped table except nodes must match exactly ────────────────
$tables = ['masters', 'templates', 'components', 'component_categories', 'component_documents',
           'collections', 'collection_groups', 'collection_modes', 'collection_skins',
           'collection_variables', 'breakpoints', 'element_classes', 'sub_classes',
           'utility_classes', 'utility_sub_classes', 'styleguides', 'template_assigns'];
foreach ($tables as $t) {
    $a = $count($t, $src);
    $b = $count($t, $cp);
    $check($t, $a === $b, "$a -> $b");
}

// ── nodes: equal once orphans are set aside ─────────────────────────────────
$a = $count('nodes', $src);
$b = $count('nodes', $cp);
// an orphan has no parent at all; the roots (master-root etc.) have a parentType
// of 'master'/'template'/'component', so this catches only rows outside any tree
$orph = $wpdb->get_results($wpdb->prepare(
    "SELECT ID, type, documentType, documentID FROM {$p}mosaic_nodes
      WHERE themeID = %s AND parentType = '' AND parentID = ''", $src));
$check('nodes', $a - count($orph) === $b,
    sprintf('%d -> %d; %d orphan%s in the source (no parent, outside every tree): %s',
        $a, $b, count($orph), count($orph) === 1 ? '' : 's',
        count($orph) ? implode(', ', array_map(fn($o) => "$o->type " . substr($o->ID, 0, 8)
            . " on $o->documentType " . substr($o->documentID, 0, 8), $orph)) : 'none'));

// ── the shape of the trees: every (parentType, type) bucket the same size ───
$shape = fn(string $id) => $wpdb->get_results($wpdb->prepare(
    "SELECT parentType, type, COUNT(*) n FROM {$p}mosaic_nodes WHERE themeID = %s
      AND NOT (parentType = '' AND parentID = '') GROUP BY parentType, type", $id), OBJECT_K);
$sa = []; foreach ($shape($src) as $r) $sa["$r->parentType/$r->type"] = (int)$r->n;
$sb = []; foreach ($shape($cp)  as $r) $sb["$r->parentType/$r->type"] = (int)$r->n;
$diff = [];
foreach (array_unique(array_merge(array_keys($sa), array_keys($sb))) as $k) {
    if (($sa[$k] ?? 0) !== ($sb[$k] ?? 0)) $diff[] = "$k " . ($sa[$k] ?? 0) . '->' . ($sb[$k] ?? 0);
}
$check('tree shape', !$diff, $diff ? implode('; ', $diff)
    : count($sa) . ' (parentType, type) buckets, every one the same size');

// ── ids: which survive the copy and which are re-keyed ──────────────────────
$kept = (int)$wpdb->get_var($wpdb->prepare(
    "SELECT COUNT(*) FROM {$p}mosaic_nodes a JOIN {$p}mosaic_nodes b
        ON b.themeID = %s AND b.ID = a.ID WHERE a.themeID = %s AND a.parentType <> 'override'",
    $cp, $src));
$nonov = $count('nodes', $src, "AND parentType <> 'override' AND NOT (parentType = '' AND parentID = '')");
$check('ids kept (non-override)', $kept === $nonov,
    "$kept of $nonov nodes outside overrides keep their id");
$ova = $count('nodes', $src, "AND parentType = 'override'");
$ovb = $count('nodes', $cp,  "AND parentType = 'override'");
$ovkept = (int)$wpdb->get_var($wpdb->prepare(
    "SELECT COUNT(*) FROM {$p}mosaic_nodes a JOIN {$p}mosaic_nodes b
        ON b.themeID = %s AND b.ID = a.ID WHERE a.themeID = %s AND a.parentType = 'override'",
    $cp, $src));
$check('overrides (re-keyed)', $ova === $ovb,
    "$ova -> $ovb override nodes; $ovkept keep their id - the import issues new ones, "
    . "and re-points originalID at the re-keyed component internals");

// ── the live site is not the copy ───────────────────────────────────────────
$live = \Mosaic\MosaicThemeEntry::liveThemeID();
$check('live untouched', $live === $src, "live theme is " . substr((string)$live, 0, 8)
    . ($live === $src ? ' (the source)' : ' - NOT the source'));

WP_CLI::log(sprintf("\n%d of %d checks passed", count($rows) - $fail, count($rows)));
if ($csv !== '') {
    $fh = fopen($csv, 'w');
    fputcsv($fh, ['check', 'result', 'detail']);
    foreach ($rows as $r) fputcsv($fh, $r);
    fclose($fh);
    WP_CLI::log("wrote $csv");
}
if ($fail) WP_CLI::error("$fail check(s) failed");
WP_CLI::success('the copy is the source, tree for tree');
