<?php
/**
 * Delete a Mosaic theme completely, through the plugin's own deletion.
 *
 *   wp eval-file theme_delete.php <themeID>
 *
 * A theme is nineteen tables' worth of rows plus a generated WordPress theme
 * folder, a WP global-styles post, template assigns, and - if an admin was
 * previewing it - a test-mode user meta. ThemesModel::deleteThemeByID() is the one
 * routine that removes all of it in the right order inside a transaction, and it is
 * what the plugin itself calls when an import replaces a theme. No REST route
 * exposes it; this file does.
 *
 * It refuses the live theme. Every theme_zip.py import in test mode leaves a theme
 * behind, and this is how one is taken away again; the live one is not a mistake
 * anyone should be able to make with a typo.
 */
$args = isset($args) ? $args : [];
$id   = isset($args[0]) ? trim($args[0]) : '';

if (!preg_match('/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i', $id)) {
    WP_CLI::error('usage: wp eval-file theme_delete.php <themeID>');
}
if (!class_exists('\Mosaic\Themes\ThemesModel')) {
    WP_CLI::error('Mosaic is not loaded');
}

$live = \Mosaic\MosaicThemeEntry::liveThemeID();
if ($live === $id) {
    WP_CLI::error("refusing: $id is the LIVE theme");
}

global $wpdb;
$p = $wpdb->prefix;
$row = $wpdb->get_row($wpdb->prepare("SELECT ID, name FROM {$p}mosaic_themes WHERE ID = %s", $id));
if (!$row) {
    WP_CLI::error("no theme $id");
}
$before = [];
foreach (['nodes', 'masters', 'templates', 'components', 'collection_variables', 'template_assigns'] as $t) {
    $before[$t] = (int)$wpdb->get_var($wpdb->prepare("SELECT COUNT(*) FROM {$p}mosaic_{$t} WHERE themeID = %s", $id));
}

\Mosaic\Themes\ThemesModel::getInstance()->deleteThemeByID($id);

$left = 0;
foreach (array_keys($before) as $t) {
    $left += (int)$wpdb->get_var($wpdb->prepare("SELECT COUNT(*) FROM {$p}mosaic_{$t} WHERE themeID = %s", $id));
}
$gone = !$wpdb->get_var($wpdb->prepare("SELECT ID FROM {$p}mosaic_themes WHERE ID = %s", $id));

WP_CLI::log(sprintf('deleted %s "%s": %s', $id, $row->name,
    implode(', ', array_map(fn($k, $v) => "$k=$v", array_keys($before), $before))));
if ($gone && $left === 0) {
    WP_CLI::success('theme row and every scoped row are gone');
} else {
    WP_CLI::error("theme row gone: " . var_export($gone, true) . ", scoped rows left: $left");
}
