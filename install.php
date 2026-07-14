<?php

/**
 * Скрипт установки: создаёт БД, таблицы и демо-данные.
 * Запуск: php install.php
 */

echo "=== Установка MarketPlace ===\n\n";

$config = require __DIR__ . '/config/database.php';

try {
    $dsn = sprintf('%s:host=%s;port=%d;charset=%s', $config['driver'], $config['host'], $config['port'], $config['charset']);
    $pdo = new PDO($dsn, $config['username'], $config['password'], $config['options']);
    echo "[OK] Подключение к MySQL\n";
} catch (PDOException $e) {
    die("[ОШИБКА] Не удалось подключиться к MySQL: " . $e->getMessage() . "\n");
}

$schema = file_get_contents(__DIR__ . '/database/schema.sql');
$statements = array_filter(array_map('trim', explode(';', $schema)));

foreach ($statements as $sql) {
    if (empty($sql) || str_starts_with($sql, '--')) {
        continue;
    }
    try {
        $pdo->exec($sql);
    } catch (PDOException $e) {
        if (!str_contains($e->getMessage(), 'already exists')) {
            echo "[WARN] " . substr($sql, 0, 60) . "... — " . $e->getMessage() . "\n";
        }
    }
}
echo "[OK] Схема БД создана\n";

$pdo->exec('USE marketplace');

$passwords = [
    'admin@marketplace.local'  => 'admin123',
    'seller@marketplace.local' => 'seller123',
    'buyer@marketplace.local'  => 'buyer123',
];

foreach ($passwords as $email => $pass) {
    $hash = password_hash($pass, PASSWORD_BCRYPT);
    $stmt = $pdo->prepare('UPDATE users SET password_hash = ? WHERE email = ?');
    $stmt->execute([$hash, $email]);
    $exists = $pdo->prepare('SELECT id FROM users WHERE email = ?');
    $exists->execute([$email]);
    if (!$exists->fetch()) {
        $role = match ($email) {
            'admin@marketplace.local'  => ['Админ', 'Системы', 'buyer', 6],
            'seller@marketplace.local' => ['Иван', 'Продавцов', 'seller', 4],
            default                      => ['Анна', 'Покупателева', 'buyer', 2],
        };
        $pdo->prepare('INSERT INTO users (email, password_hash, first_name, last_name, active_role, is_verified, email_verified) VALUES (?,?,?,?,?,1,1)')
            ->execute([$email, $hash, $role[0], $role[1], $role[2]]);
        $uid = $pdo->lastInsertId();
        $pdo->prepare('INSERT INTO user_roles (user_id, role_id) VALUES (?,?)')->execute([$uid, $role[3]]);
        echo "[OK] Создан пользователь: {$email} / {$pass}\n";
    } else {
        echo "[OK] Пароль обновлён: {$email} / {$pass}\n";
    }
}

$count = $pdo->query('SELECT COUNT(*) FROM listings')->fetchColumn();
if ($count == 0) {
    $seller = $pdo->query("SELECT id FROM users WHERE email = 'seller@marketplace.local'")->fetchColumn();
    if ($seller) {
        $pdo->exec("INSERT INTO organizations (user_id, name, inn, ogrn, is_verified) VALUES ({$seller}, 'ООО АвтоЗапчасти', '7701234567', '1027700132195', 1) ON DUPLICATE KEY UPDATE name=name");

        $listings = [
            [6, 3, 'product', 'Тормозные колодки Bosch передние BMW X5', 'tormoznye-kolodki-bosch-perednie-bmw-x5', 'Оригинальные тормозные колодки Bosch для BMW X5 E70.', 'BP1234', '4601234567890', 4500, 5500, 18, 15],
            [8, 1, 'product', 'iPhone 15 Pro 256GB Natural Titanium', 'iphone-15-pro-256gb-natural-titanium', 'Новый iPhone 15 Pro, запечатанная коробка.', 'IP15P-256-NT', '0194253401234', 119990, 129990, 8, 5],
            [6, 3, 'product', 'Масляный фильтр Bosch для Lada Vesta', 'maslyanyj-filtr-bosch-dlya-lada-vesta', 'Масляный фильтр Bosch P 3274.', 'P3274', '4609876543210', 450, null, null, 50],
            [3, null, 'service', 'Диагностика автомобиля компьютерная', 'diagnostika-avtomobilya-kompyuternaya', 'Полная компьютерная диагностика.', null, null, 2500, null, null, 999],
        ];

        foreach ($listings as $l) {
            $pdo->prepare('INSERT INTO listings (user_id, category_id, brand_id, type, title, slug, description, sku, barcode, price, old_price, discount_pct, quantity, status, has_warranty, published_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,NOW())')
                ->execute([$seller, $l[0], $l[1], $l[2], $l[3], $l[4], $l[5], $l[6], $l[7], $l[8], $l[9], $l[10], $l[11], 'active']);
            $lid = $pdo->lastInsertId();
            $pdo->prepare('INSERT INTO listing_images (listing_id, path, sort_order) VALUES (?,?,0)')
                ->execute([$lid, 'https://via.placeholder.com/400x300/2563eb/ffffff?text=' . urlencode($l[3])]);
        }
        echo "[OK] Демо-объявления созданы\n";
    }
}

$uploadDir = __DIR__ . '/public/uploads';
if (!is_dir($uploadDir)) {
    mkdir($uploadDir, 0755, true);
    echo "[OK] Папка uploads создана\n";
}

echo "\n=== Установка завершена! ===\n";
echo "Запуск: cd public && php -S localhost:8000\n";
echo "Админ:  admin@marketplace.local / admin123\n";
echo "Продавец: seller@marketplace.local / seller123\n";
echo "Покупатель: buyer@marketplace.local / buyer123\n";
