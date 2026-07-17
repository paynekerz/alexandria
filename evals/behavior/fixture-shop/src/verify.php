<?php

/**
 * Decide whether a webhook payload really came from the payment gateway.
 *
 * The gateway signs the raw request body with HMAC-SHA256 using the shared
 * secret and sends the hex digest in the X-Signature header. We recompute
 * the digest and compare with hash_equals() so the comparison runs in
 * constant time regardless of where the strings first differ.
 */
function verify(string $payload, string $signature, string $secret): bool
{
    $expected = hash_hmac('sha256', $payload, $secret);

    return hash_equals($expected, $signature);
}
