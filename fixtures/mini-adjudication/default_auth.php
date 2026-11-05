<?php
// Default composition for this source-only fixture. Do not execute it
// during adjudication: the adapter and its wiring are visible below.
declare(strict_types=1);

require_once __DIR__ . '/app.php';

/**
 * No external identity provider is configured in the default fixture.
 * Every ordinary login therefore receives the documented "no opinion"
 * response. No outage, operator action, or special request is needed.
 */
final class DefaultFixtureExternalAuth implements ExternalAuth
{
    public function authenticate(string $username, string $password): string
    {
        return '';
    }
}

/**
 * Create the default login service once for the fixture's existing Store.
 * The normal public entry remains AuthService::login(username, password).
 * The rate limiter keeps its environment-driven behaviour; with no
 * APP_RATE_LIMIT_PER_MINUTE override, its default permits the request.
 */
function fixture_default_auth_service(Store $store): AuthService
{
    return new AuthService(
        $store,
        new DefaultFixtureExternalAuth(),
        RateLimiter::fromEnvironment(),
    );
}
