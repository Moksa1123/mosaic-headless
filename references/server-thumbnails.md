# Server-side thumbnails without root

Mosaic can capture page and component thumbnails on the server with headless
Chrome. Its documentation installs Chrome with `apt` as root, which a managed host
(Cloudways and the like) does not allow. The procedure below needs no root. It was
worked through end to end on a live client site (Debian 12, Mosaic 1.0.10) - Mosaic's
"generate thumbnails" completed for every template - and each step is checked
against the plugin source.

## How Mosaic finds Chrome

`Mosaic/Common/ScreenshotChrome.php`:

- the binary is, in order: the constant **`MOSAIC_CHROME_BINARY`**, then whatever the
  filter **`mosaic_chrome_binary_path`** returns, then chrome-php's `AutoDiscover`,
  which also honours a `CHROME_PATH` server variable;
- `isChromiumAvailable()` checks only that `shell_exec`, `proc_open` and
  `is_executable` exist and that the binary is executable;
- launch options pass through **`mosaic_screenshot_chrome_options`**, and Mosaic
  already runs with `noSandbox`.

So anything executable at a path you name will do, including a wrapper script.

## The procedure

**1. Check from a web request, never from WP-CLI.** PHP-FPM and the CLI have
different `disable_functions`: on the client host FPM disabled `proc_open`,
`proc_close`, `proc_terminate` and `shell_exec` while the CLI did not, so `wp eval`
said Chrome was available and every web request said it was not. Put a temporary
PHP file in the web root that loads `wp-load.php` and prints
`function_exists('proc_open')`, `function_exists('shell_exec')` and
`\Mosaic\Common\ScreenshotChrome::isChromiumAvailable()`; fetch it once; delete it
straight away.

**2. Install Chrome as the site's own user**, in a directory the app owns outside
the web root (e.g. the app's `private_html/chrome`):

- download `chrome-headless-shell` from Chrome for Testing - the version is in
  `https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_STABLE`, the
  archive at
  `https://storage.googleapis.com/chrome-for-testing-public/<version>/linux64/chrome-headless-shell-linux64.zip`;
- `ldd chrome-headless-shell | grep "not found"` - on the client host:
  `libnspr4`, `libnss3`, `libnssutil3`, `libatk-1.0`, `libatk-bridge-2.0`,
  `libXcomposite`, `libXdamage`, `libatspi`;
- `apt-get download libnspr4 libnss3 libatk1.0-0 libatk-bridge2.0-0 libxcomposite1
  libxdamage1 libatspi2.0-0` (no root needed), unpack each with `dpkg-deb -x`, and
  copy the `*.so*` files into `chrome/lib`; repeat `ldd` until nothing is missing;
- a wrapper `chrome/chrome`, mode 755, that sets `LD_LIBRARY_PATH` to `chrome/lib`
  and `exec`s `chrome-headless-shell "$@"`.

CJK text needs a CJK font the system already has (`fc-list :lang=zh`); that host's
Droid Sans Fallback was enough.

**3. Point Mosaic at the wrapper**:
`wp config set MOSAIC_CHROME_BINARY /path/to/chrome/chrome --type=constant`.

**4. Let PHP-FPM run it.** Remove exactly `proc_open`, `proc_close`, `proc_terminate`
and `shell_exec` from the app's `php_admin_value[disable_functions]` and keep the rest.
On Cloudways that is Application Settings → PHP-FPM Settings, or the API's
`app_fpm_settings_update` (which takes the whole settings block, base64-encoded);
either way it changes only that app. chrome-php and symfony/process use
`proc_open` / `proc_close` / `proc_terminate` / `proc_get_status`; Mosaic's own
detection uses `shell_exec`.

**5. Repeat step 1.** `isChromiumAvailable()` from the web request must now be true.

**6. Turn the setting on by hand.** `serverSideThumbnailRender` is stored the first
time Mosaic reads its settings, as whatever `isChromiumAvailable()` said then, and is
never re-evaluated (`MosaicSettingsMResource.php`). Reload Mosaic → Settings: the
"Server-side thumbnail rendering" switch appears in the same group as "Load scripts
inline" and "WordPress emoji support" - only once Chrome is available - so switch it
on and save.

**7. Let the capture past a full-screen entrance.** A page with an entrance veil or
overlay is photographed as the veil: the client's homepage came out as a single flat
colour, a 760-byte JPEG. Have the front end drop the veil when
`/HeadlessChrome/.test(navigator.userAgent)` or `window.self !== window.top`. A
Playwright check of that entrance then needs a context whose user agent does not
contain `HeadlessChrome`, or it measures the veil-less page.

**8. Generate the thumbnails** from Mosaic. A 600x338 capture took about 2.6s.

Steps 2-4 belong to the app, not the site: a new server or a cloned app needs them
again; moving the same app to another domain does not.
