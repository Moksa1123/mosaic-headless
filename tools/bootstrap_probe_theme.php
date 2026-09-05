<?php
/**
 * Build a throwaway Mosaic theme + master + template on the current site, from scratch.
 *
 *   wp eval-file bootstrap_probe_theme.php [--user=1]
 *
 * Prints THEME_ID / MASTER_ID / TEMPLATE_ID / BODY_DIV_ID as key=value lines for a
 * harness to consume.
 *
 * Why this exists: Mosaic's own "new theme" path goes through the onboarding wizard,
 * which fetches from account.mosaicbuilder.com and needs an active licence. The
 * plugin's internal classes do not — EditorInstanceWithNewTheme->heal() builds the
 * whole default document (master-root > document > body > three divs) on its own.
 * That makes a licence-free, repeatable test fixture possible, which is the only
 * reason the write path in this skill could be verified at all.
 *
 * Set MOSAIC_PROBE_RESET=1 in the environment to delete every existing Mosaic theme
 * first. That is destructive and is meant for a scratch site only.
 */

use Mosaic\Common\UUID;
use Mosaic\Themes\ThemeRevisionRecord;
use Mosaic\EditorInstance\Theme\ThemeScopedTheme\EditorInstanceWithNewTheme;
use Mosaic\WPTheme\WPThemeManager;

global $wpdb;

if (getenv('MOSAIC_PROBE_RESET') === '1') {
    $tables = [
        'nodes', 'templates', 'template_assigns', 'masters', 'styleguides',
        'components', 'component_documents', 'component_categories',
        'element_classes', 'sub_classes', 'utility_classes', 'utility_sub_classes',
        'breakpoints', 'collections', 'collection_modes', 'collection_skins',
        'collection_groups', 'collection_variables', 'themes',
    ];
    foreach ($tables as $t) {
        $wpdb->query("DELETE FROM {$wpdb->prefix}mosaic_{$t}");
    }
    echo "reset=1\n";
}

$themeID = UUID::generate();
$row     = (object)[
    'ID'       => $themeID,
    'name'     => 'HeadlessProbe',
    'ordering' => 'a0',
    'status'   => 'publish',
    'revision' => '',
    'version'  => '',
    'data'     => (object)[],
];

$editorInstance = new EditorInstanceWithNewTheme(new ThemeRevisionRecord($row, true));
$editorInstance->load();
$editorInstance->heal();          // builds the default master + node tree
$editorInstance->pushToDB();

$theme = $editorInstance->getThemeMResource();
WPThemeManager::createThemeOnCurrentSite($theme->getID(), $theme->getName(), $theme->getRevision());

echo "THEME_ID=" . $theme->getID() . "\n";
echo "THEME_REVISION=" . $theme->getRevision() . "\n";

// heal() on the theme instance stops at the theme row - it does NOT create a master.
// The master, its node tree and the template are committed over REST by the harness,
// so the documented checkout/commit protocol is what actually gets exercised rather
// than a PHP shortcut around it.
echo "WP_THEME=" . basename(WPThemeManager::getThemePath($theme->getID())) . "\n";
