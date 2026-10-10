# Server-side thumbnails without root

Mosaic can capture page and component thumbnails on the server with headless
Chrome. Its documentation installs Chrome with `apt` as root, which a managed host
(Cloudways and the like) does not allow. This is a route that needs no root, worked
through on a client build (Debian 12, Mosaic 1.0.10) and checked against the source.

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

## The install, as the site's own user

1. **Get `chrome-headless-shell`** from Chrome for Testing into a directory the
   app owns (outside the web root): the version is in
   `https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_STABLE`, the
   archive at
   `https://storage.googleapis.com/chrome-for-testing-public/<version>/linux64/chrome-headless-shell-linux64.zip`.
2. **Supply the libraries it cannot find.** `ldd chrome-headless-shell | grep "not found"`
   listed `libnspr4`, `libnss3`, `libnssutil3`, `libatk-1.0`, `libatk-bridge-2.0`,
   `libXcomposite`, `libXdamage` and `libatspi` on that host. `apt-get download` does
   not need root: download `libnspr4 libnss3 libatk1.0-0 libatk-bridge2.0-0
   libxcomposite1 libxdamage1 libatspi2.0-0`, unpack each with `dpkg-deb -x`, and copy
   the `*.so*` files into a `lib/` beside the binary. Run `ldd` again until nothing is
   missing.
3. **Wrap it**: a script, mode 755, that sets `LD_LIBRARY_PATH` to that `lib/` and
   `exec`s `chrome-headless-shell "$@"`.
4. **Point Mosaic at the wrapper**:
   `wp config set MOSAIC_CHROME_BINARY /path/to/wrapper --type=constant`.

CJK text needs a CJK font the system already has (`fc-list :lang=zh`); that host's
Droid Sans Fallback was enough.

## Two things that make it look broken when it is not

**Check from a web request, not from WP-CLI.** PHP-FPM on that host disables
`proc_open`, `proc_close`, `proc_terminate` and `shell_exec` by default; the CLI does
not. So `wp eval` reports `isChromiumAvailable()` true while every web request sees
false - and the Mosaic settings page does not even show the "Server-side thumbnail
rendering" switch. Remove those four from the app's own `disable_functions` (on
Cloudways: Application Settings → PHP-FPM, or the API's FPM settings), and verify
with a temporary PHP file that loads `wp-load.php` and calls the check, deleted
afterwards. chrome-php and symfony/process use `proc_open` / `proc_close` /
`proc_terminate` / `proc_get_status`; Mosaic's own detection uses `shell_exec`.

**The setting is decided once.** `serverSideThumbnailRender` is stored the first time
the settings are read, as whatever `isChromiumAvailable()` said at that moment
(`MosaicSettingsMResource.php`), and never re-evaluated. After installing Chrome,
turn it on in the settings page by hand.

A capture of a working install took about 2.6s for a 600x338 thumbnail.

## When it photographs the wrong thing

A page with a full-screen entrance veil photographs the veil. Give the veil a way
out for a capture: the front end can drop it when the user agent matches
`HeadlessChrome` or when `window.self !== window.top`.

The install lives in the app's directory, so a cloned app or a new server needs it
again.
