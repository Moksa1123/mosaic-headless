<?php
/**
 * Which template and master serve each post - read only, prints JSON.
 *
 *   wp eval-file tools/list_bindings.php <themeID> > bindings.json
 *
 * Mosaic's REST API lists templates and masters but not which post a template is
 * bound to; that is wp_mosaic_template_assigns. sync_nodes.py reads this file to
 * update a site in place: it needs each page's own template, and it refuses to run
 * when the pages it was given sit on more than one master (a "split" site, where an
 * edit to the header reaches only some pages).
 *
 * Output: {"themeID": "...", "posts": {"<post id>": {"template": "<id>",
 *          "master": "<id>", "name": "<template name>"}}}
 * Arguments are positional: WP-CLI takes any --flag as its own.
 */
global $wpdb;
$args = isset($args) ? $args : [];
$theme = isset($args[0]) ? trim($args[0]) : '';
if (!preg_match('/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i', $theme)) {
    WP_CLI::error('usage: wp eval-file list_bindings.php <themeID>');
}
$rows = $wpdb->get_results($wpdb->prepare(
    "SELECT a.typeIdentifier AS post, t.ID AS template, t.masterID AS master, t.name AS name
       FROM {$wpdb->prefix}mosaic_template_assigns a
       JOIN {$wpdb->prefix}mosaic_templates t ON t.ID = a.parentID AND t.themeID = a.themeID
      WHERE a.themeID = %s AND a.type = 'post' AND a.parentType = 'template'",
    $theme
));
if ($wpdb->last_error !== '') {
    WP_CLI::error($wpdb->last_error);
}
$out = ['themeID' => $theme, 'posts' => []];
foreach ($rows as $r) {
    $out['posts'][(string) $r->post] = ['template' => $r->template, 'master' => $r->master, 'name' => $r->name];
}
echo wp_json_encode($out, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE) . "\n";
