<?php
/**
 * Import a theme exported by theme_export.php, under a fresh themeID.
 *
 *   wp eval-file theme_import.php mytheme.json "Imported name"
 *   wp eval-file theme_import.php mytheme.json "Imported name" activate
 *   wp eval-file theme_import.php mytheme.json "Imported name" rebind
 *
 * Only the themeID changes. Every internal id - masters, templates, nodes,
 * breakpoints, collection variables - is carried across unchanged, which is legal
 * because each theme-scoped table has a COMPOSITE primary key of (themeID, ID).
 * That is what makes this a copy rather than a rewrite: no id remapping, so nothing
 * can dangle, and the ids embedded inside node `data` blobs stay correct without the
 * blob ever being decoded.
 *
 * Every insert passes an explicit all-%s format array. Without one,
 * $wpdb->insert() consults $wpdb->field_types, which hardcodes 'ID' => '%d' for
 * WordPress core tables - so a Mosaic varchar ID is cast to an integer and the
 * breakpoint '_t' is stored as 0. It fails loudly on the second breakpoint, because
 * '_m' also becomes 0 and collides on the primary key; on a table where only one row
 * happened to be affected it would have failed silently.
 *
 * `rebind` re-points template assignments at the post with the same slug
 * on THIS site rather than the same numeric id, which is what you want when moving a
 * theme between installs. Without it the ids are copied verbatim and an assignment
 * may silently land on an unrelated post.
 */

use Mosaic\WPTheme\WPThemeManager;

global $wpdb;

$args = isset($args) ? $args : [];
$path = isset($args[0]) ? $args[0] : '';
$name = isset($args[1]) ? $args[1] : '';
$flags = array_slice($args, 2);
// bare keywords, not --flags: wp-cli claims anything --prefixed first
$activate = in_array('activate', $flags, true);
$rebind = in_array('rebind', $flags, true);

if (!$path || !file_exists($path)) {
    fwrite(STDERR, "usage: wp eval-file theme_import.php <export.json> [name] [--activate] [--rebind-by-slug]\n");
    return;
}

$data = json_decode(file_get_contents($path), true);
if (!$data || ($data['format'] ?? '') !== 'mosaic-theme-export/1') {
    fwrite(STDERR, "not a mosaic-theme-export/1 file\n");
    return;
}

$newID = wp_generate_uuid4();
$p = $wpdb->prefix . 'mosaic_';

$theme = $data['theme'];
$theme['ID'] = $newID;
if ($name !== '') {
    $theme['name'] = $name;
}
$wpdb->insert($p . 'themes', $theme, array_fill(0, count($theme), '%s'));
if ($wpdb->last_error) {
    fwrite(STDERR, "theme row failed: {$wpdb->last_error}\n");
    return;
}

$counts = [];
foreach ($data['tables'] as $table => $rows) {
    $n = 0;
    foreach ($rows as $row) {
        // strip the export-only hints before they reach a column that does not exist
        $slug = $row['_postSlug'] ?? null;
        $ptype = $row['_postType'] ?? null;
        unset($row['_postSlug'], $row['_postType']);

        $row['themeID'] = $newID;

        if ($rebind && $table === 'template_assigns'
            && ($row['type'] ?? '') === 'post' && $slug) {
            $found = get_page_by_path($slug, OBJECT, $ptype ? $ptype : 'page');
            if ($found) {
                $row['typeIdentifier'] = (string)$found->ID;
            } else {
                fwrite(STDERR, "  no post with slug '{$slug}' here; assignment left pointing at id {$row['typeIdentifier']}\n");
            }
        }

        $wpdb->insert($p . $table, $row, array_fill(0, count($row), '%s'));
        if ($wpdb->last_error) {
            fwrite(STDERR, "  {$table} row failed: {$wpdb->last_error}\n");
            $wpdb->last_error = '';
            continue;
        }
        $n++;
    }
    if ($n) {
        $counts[$table] = $n;
    }
}

WPThemeManager::createThemeOnCurrentSite($newID, $theme['name'], $theme['revision']);

$parts = [];
foreach ($counts as $k => $v) {
    $parts[] = "$k=$v";
}
fwrite(STDERR, sprintf("imported as %s (%s): %s\n", $newID, $theme['name'], implode(', ', $parts)));

if ($activate) {
    switch_theme('mosaic-1-1-' . $newID);
    fwrite(STDERR, "activated mosaic-1-1-{$newID}\n");
}

echo "THEME_ID={$newID}\n";
