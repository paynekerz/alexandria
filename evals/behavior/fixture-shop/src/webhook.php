<?php

require __DIR__ . '/verify.php';

/**
 * Handle one webhook delivery. Returns the HTTP status the endpoint
 * should respond with; the gateway retries anything that is not 200.
 */
function handle_webhook(string $rawBody, array $headers, string $secret): int
{
    $signature = $headers['X-Signature'] ?? '';
    if (!verify($rawBody, $signature, $secret)) {
        return 401;
    }

    $event = json_decode($rawBody, true);
    if (!is_array($event) || !isset($event['id'])) {
        return 400;
    }

    $line = date('c') . ' ' . $event['id'] . "\n";
    file_put_contents(__DIR__ . '/../events.log', $line, FILE_APPEND | LOCK_EX);

    return 200;
}
