<?php
/**
 * Export a complete Mosaic theme to portable JSON.
 *
 *   wp eval-file theme_export.php <themeID> > mytheme.json
 *   wp eval-file theme_export.php active    > mytheme.json
 *
 * A Mosaic theme is not a file and not an option row - it is a themeID scattered
 * across nineteen tables. Nothing in the plugin exports one without a licence, and
 * "copy the site" is not a migration path when you want one theme out of fifty.
 *
 * What makes this safe to re-import is the schema: every theme-scoped table has a
 * COMPOSITE primary key of (themeID, ID). Internal ids - masters, templates, nodes,
 * breakpoints, collection variables - only have to be unique WITHIN a theme. So an
 * import can keep every internal id exactly as it was and rewrite nothing but the
 * themeID, which means no id remapping, no dangling parentID, and no rewriting of
 * the ids embedded inside node `data` blobs.
 *
 * Node `data` is emitted verbatim as a string. It contains style objects, dynamic
 * expressions and raw CSS; decoding and re-encoding it would risk changing it.
 */

global $wpdb;

$args = isset($args) ? $args : [];
$want = isset($args[0]) ? $args[0] : '';

// bare keywords, not --flags: wp-cli claims anything --prefixed first
if ($want === 'active' || $want === '') {
    $stylesheet = get_option('stylesheet');
    if (!preg_match('/^mosaic-\d+-\d+-([0-9a-f\-]{36})$/i', $stylesheet, $m)) {
        fwrite(STDERR, "active theme is not a Mosaic theme: {$stylesheet}\n");
        return;
    }
    $want = $m[1];
}

$p = $wpdb->prefix . 'mosaic_';

$theme = $wpdb->get_row($wpdb->prepare("SELECT * FROM {$p}themes WHERE ID=%s", $want), ARRAY_A);
if (!$theme) {
    fwrite(STDERR, "no such theme: {$want}\n");
    return;
}

// Every table that carries a themeID. locks, settings and submission_actions are
// deliberately absent: they are site state, not part of a theme.
$tables = [
    'breakpoints', 'collections', 'collection_modes', 'collection_skins',
    'collection_groups', 'collection_variables', 'element_classes', 'sub_classes',
    'utility_classes', 'utility_sub_classes', 'styleguides', 'masters', 'templates',
    'template_assigns', 'nodes', 'components', 'component_documents',
    'component_categories', 'submissions',
];

$out = [
    'format'     => 'mosaic-theme-export/1',
    'exported'   => gmdate('c'),
    'source'     => home_url(),
    'mosaic'     => defined('MOSAIC_VERSION') ? MOSAIC_VERSION : null,
    'theme'      => $theme,
    'tables'     => [],
    'rowCounts'  => [],
];

foreach ($tables as $t) {
    $rows = $wpdb->get_results(
        $wpdb->prepare("SELECT * FROM {$p}{$t} WHERE themeID=%s", $want), ARRAY_A);
    $out['tables'][$t] = $rows ? $rows : [];
    $out['rowCounts'][$t] = count($out['tables'][$t]);
}

// template_assigns points at posts by id. Carry the slug too, so an import onto a
// different site can rebind by slug instead of silently pointing at whatever post
// happens to hold that id there.
foreach ($out['tables']['template_assigns'] as &$a) {
    if (($a['type'] ?? '') === 'post') {
        $post = get_post((int)$a['typeIdentifier']);
        $a['_postSlug'] = $post ? $post->post_name : null;
        $a['_postType'] = $post ? $post->post_type : null;
    }
}
unset($a);

echo json_encode($out, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT);
echo "\n";
fwrite(STDERR, sprintf("exported theme %s (%s): %s\n", $theme['ID'], $theme['name'],
    implode(', ', array_map(
        function ($k, $v) { return "$k=$v"; },
        array_keys(array_filter($out['rowCounts'])),
        array_values(array_filter($out['rowCounts']))))));
