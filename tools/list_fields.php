<?php
/**
 * Every dynamic variable and loop Mosaic exposes for one post - the exact names
 * `@VAR('post/<name>')` and `@LOOP('post/<name>')` take - with the value each
 * resolves to on that post. Custom fields (ACF, Meta Box, plain post meta) included,
 * with the derived properties a structured field grows (`__label`, `__url`, `__id`,
 * `__title`, `__target`) and the row variables inside each loop.
 *
 *     wp eval-file tools/list_fields.php <post_id> [csv]
 *
 * Reads the same schema the frontend evaluates (VariableProviderPost), so a name that
 * is not printed here does not exist for that post, whatever the field plugin calls it.
 * Loop names are the plugin's own: `loop<key>` for most fields, `loop-<key>` for an ACF
 * group. Row variables live under the loop node's `loopNamespace` (default `item`).
 */

use Mosaic\Compatibility\VariableProvider\AbstractVariableProvider;
use Mosaic\Compatibility\VariableProvider\VariableProvider;
use Mosaic\Compatibility\WordPress\PathContext\VariableProviderPost;

$postID = (int)($args[0] ?? 0);
$asCsv  = ($args[1] ?? '') === 'csv';
$post   = get_post($postID);
if (!$post) {
    WP_CLI::error("no post $postID");
}

$provider = new VariableProvider(VariableProviderPost::getVariableProviderDefinition(get_post_type_object($post->post_type), $postID));
$ref      = new ReflectionClass(AbstractVariableProvider::class);
$vars     = $ref->getProperty('schemaVariables');
$vars->setAccessible(true);
$loops = $ref->getProperty('schemaLoops');
$loops->setAccessible(true);
$record = $ref->getProperty('currentRecord');
$record->setAccessible(true);
$record->setValue($provider, $post);

$rows = [];
foreach ($vars->getValue($provider) as $name => $variable) {
    $value = '';
    try {
        $value = (string)$variable->getValue($post);
    } catch (Throwable $e) {
        $value = 'ERR ' . $e->getMessage();
    }
    $rows[] = ['variable', "post/$name", $variable->getLabel(), $value];
}
foreach ($loops->getValue($provider) as $name => $loop) {
    $count = 0;
    $inner = [];
    try {
        $lp = $loop->toLoop($post);
        if ($lp) {
            $count = $lp->getTotalItems();
            if ($count > 0) {
                // read row 1 the way the evaluator does: seek, then getVariable per name
                $lp->seek(0);
                $lv = $ref->getProperty('schemaVariables');
                $lv->setAccessible(true);
                foreach (array_keys($lv->getValue($lp)) as $n) {
                    $val = '';
                    try {
                        $val = (string)$lp->getVariable($n);
                    } catch (Throwable $e) {
                        $val = '?';
                    }
                    $inner[] = "$n=" . mb_substr(str_replace(PHP_EOL, ' ', $val), 0, 30);
                }
            }
        }
    } catch (Throwable $e) {
        $inner = ['ERR ' . $e->getMessage()];
    }
    $rows[] = ['loop', "post/$name", $loop->getLabel(), $count . ' items; first row: ' . implode(' | ', $inner)];
}

if ($asCsv) {
    $out = fopen('php://output', 'w');
    fputcsv($out, ['kind', 'name', 'label', 'value']);
    foreach ($rows as $r) {
        fputcsv($out, $r);
    }
    fclose($out);
} else {
    foreach ($rows as [$kind, $name, $label, $value]) {
        printf("%-8s %-34s %-28s %s\n", $kind, $name, mb_substr($label, 0, 28), mb_substr(str_replace("\n", ' ', $value), 0, 80));
    }
}
