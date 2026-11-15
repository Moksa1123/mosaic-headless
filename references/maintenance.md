# Maintenance: regenerating everything

Moved out of SKILL.md on 2026-11-16 (skill SOP pass).

## Regenerating everything

```bash
python tools/extract_node_types.py       <plugin-root> data/
python tools/extract_pluggables.py       <plugin-root> data/
python tools/extract_placement.py        <plugin-root> data/
python tools/extract_default_children.py <plugin-root> data/   # now also records heal-inserted children
python tools/extract_style_properties.py <plugin-root> data/
python tools/extract_interactions.py     <plugin-root> data/
python tools/extract_dynamic_variables.py <plugin-root> data/

# and then, always: a table extracted BEFORE its extractor was repaired keeps
# describing the old source and ships silently. Row counts cannot see it and the
# release gate never sees the plugin. Run this after ANY change to an extractor,
# not only after a plugin upgrade.
python tools/check_tables.py              <plugin-root>
python tools/capture_live.py             data/          # from data/raw/*.json + db-columns.txt
                                                        # (raw dumps are gitignored;
                                                        #  re-capture from a live site)

# against a scratch site - DESTRUCTIVE, never point at production
python tools/sweep_node_types.py --config sweep.json --setup
python tools/sweep_node_types.py --config sweep.json --sweep --edition all
python tools/sweep_properties.py --config sweep.json
# `sites/moksa.json` is GENERATED - the package ships the readable modules it
# comes from, not 2MB of built output. Regenerate it before anything reads it:
python sites/_moksa.py

python tools/verify_rwd.py --config sweep.json --site sites/moksa.json --csv data/rwd-verification.csv
python tools/verify_browser.py --config sweep.json --site sites/moksa.json \
    --csv data/browser-verification/ --audit data/design-audit.csv
python tools/verify_intro.py --config sweep.json --site sites/moksa.json \
    --csv data/intro-verification.csv --frames shots/intro/
python tools/sweep_style_properties.py --config sweep.json --page moksa --csv data/style-verification.csv
python tools/sweep_node_properties.py  --config sweep.json --page moksa --csv data/node-property-verification.csv
python tools/sweep_style_states.py --config sweep.json --post 20 --slug probe-lab     --csv data/style-state-verification.csv
python tools/sweep_interactions.py --config sweep.json --post 20 --slug probe-lab     --csv data/interaction-verification.csv
python tools/verify_recipes.py --config sweep.json --post <ID of the probe-recipes page> --slug probe-recipes \
    --csv data/tutorial-recipes-verification.csv   # --post REBINDS that post's template: check the ID first
python tools/verify_menus.py --config sweep.json --post <ID of the menu-lab page> --slug menu-lab --csv data/menu-verification.csv
python tools/verify_loop.py --url https://site/ --window mk-loop --toggle mk-plate-title --panel mk-plate-item \
    --parts ukw-sky,ukw-sun,ukw-fuji,ukw-mist,ukw-sea,ukw-crest,ukw-boat,ukw-wave,ukw-claw,ukw-swell,ukw-key,mk-loop-seal \
    --period 14000 --csv data/loop-verification.csv
python tools/probe_accordion.py --config sweep.json --post 20 --slug probe-lab --csv data/accordion-verification.csv
python tools/from_elementor.py --data _elementor_data.json --out spec.json --report conv.csv     --uploads-base https://site/wp-content/uploads --slug converted --post 208
python tools/verify_rwd.py     --config c.json --site spec.json --csv rwd.csv
python tools/verify_browser.py --config c.json --site spec.json --csv browser.csv --audit audit.csv
python tools/verify_conversion.py --data _elementor_data.json --url https://site/converted/     --report conv.csv --prefix p2360 --rwd rwd.csv --browser browser.csv --audit audit.csv     --csv data/conversion-verification.csv
wp eval-file tools/theme_export.php active > theme.json
wp eval-file tools/theme_import.php theme.json "Copy" rebind activate
python tools/theme_zip.py export --config c.json --out theme.zip
python tools/theme_zip.py import --config c.json --zip theme.zip            # test mode
python tools/theme_zip.py import --config c.json --zip theme.zip --activate # goes live
wp eval-file tools/theme_zip_compare.php <source> <copy> theme-zip-verification.csv
wp eval-file tools/theme_delete.php <copy>
python tools/probe.py --config lab.json --cases cases.json   # ad-hoc measurement
python tools/check_placement_predicts.py
claude plugin eval . --runs 3 -j 3 --no-publish   # the skill vs no skill, 5 cases; Bash is
                                                  # not granted (no sandbox on Windows), the
                                                  # agent reads data/ instead of running mo.py
```

`bootstrap_probe_theme.php` exists because Mosaic's own new-theme flow calls
`account.mosaicbuilder.com` and needs a licence. `EditorInstanceWithNewTheme->heal()`
does not — which is what made a licence-free fixture, and therefore this whole
verification, possible.
