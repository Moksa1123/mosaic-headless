<?php
/**
 * Mint a logged-in cookie and a matching wp_rest nonce, without a browser.
 *
 *   wp eval-file mint_session.php                 # first administrator
 *   wp eval-file mint_session.php admin@site.com  # a specific account
 *
 * The catch: wp_create_nonce() mixes in wp_get_session_token(), which reads the
 * session token out of the CURRENT REQUEST's logged-in cookie. Under WP-CLI there is
 * no such cookie, so a nonce minted the obvious way is tied to an empty token while
 * the cookie carries a real one, and the REST API rejects the pair. So: create the
 * session explicitly, build the cookie around that token, then plant the cookie in
 * $_COOKIE before creating the nonce, so both sides agree on the same session.
 */
$args = isset($args) ? $args : [];

// Takes a login or email; falls back to the first administrator on the site. Never
// hardcode an account here - this file ships.
$who  = isset($args[0]) ? $args[0] : '';
$user = null;
if ($who !== '') {
    $user = strpos($who, '@') !== false ? get_user_by('email', $who)
                                        : get_user_by('login', $who);
    if (!$user) {
        echo "NO_SUCH_USER
";
        return;
    }
}
if (!$user) {
    $admins = get_users(array('role' => 'administrator', 'number' => 1));
    $user = $admins ? $admins[0] : null;
}
if (!$user) {
    echo "NO_ADMIN\n";
    return;
}

$expiration = time() + 12 * HOUR_IN_SECONDS;

$manager = WP_Session_Tokens::get_instance($user->ID);
$token   = $manager->create($expiration);

$cookie = wp_generate_auth_cookie($user->ID, $expiration, 'logged_in', $token);

$_COOKIE[LOGGED_IN_COOKIE] = $cookie;
wp_set_current_user($user->ID);

echo 'COOKIE=' . LOGGED_IN_COOKIE . '=' . $cookie . "\n";
echo 'NONCE=' . wp_create_nonce('wp_rest') . "\n";
echo 'SITEURL=' . get_option('siteurl') . "\n";
echo 'USER=' . $user->user_login . "\n";
