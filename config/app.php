<?php

return [
    'name'       => 'MarketPlace',
    'url'        => 'http://localhost:8000',
    'debug'      => true,
    'timezone'   => 'Europe/Moscow',
    'locale'     => 'ru_RU',
    'upload_path' => __DIR__ . '/../public/uploads',
    'upload_url'  => '/uploads',
    'session_name' => 'marketplace_session',
    'csrf_token_name' => '_token',
    'items_per_page' => 20,
    'commission_rate' => 0.05,
    'sms' => [
        'provider' => 'smsaero',
        'api_key'  => '',
    ],
    'payment' => [
        'default' => 'yukassa',
        'yukassa_shop_id' => '',
        'yukassa_secret'  => '',
    ],
    'recaptcha' => [
        'site_key'   => '',
        'secret_key' => '',
    ],
];
