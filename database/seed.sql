-- Демо-данные для тестирования
USE marketplace;

-- Продавец (пароль: seller123)
INSERT INTO users (email, password_hash, first_name, last_name, phone, active_role, is_verified, email_verified)
VALUES ('seller@marketplace.local', '$2y$10$8K1p/a0dL1LXMIgoEDFrwOfMQRq3.HvW9KzqKxqGxGxGxGxGxGxGxG', 'Иван', 'Продавцов', '+79001234567', 'seller', 1, 1);

-- Исправим хеш продавца через отдельный скрипт install.php
-- Покупатель (пароль: buyer123)  
INSERT INTO users (email, password_hash, first_name, last_name, active_role, email_verified)
VALUES ('buyer@marketplace.local', '$2y$10$8K1p/a0dL1LXMIgoEDFrwOfMQRq3.HvW9KzqKxqGxGxGxGxGxGxGxG', 'Анна', 'Покупателева', 'buyer', 1);

INSERT INTO user_roles (user_id, role_id) VALUES (2, 4), (3, 2);

INSERT INTO organizations (user_id, name, inn, ogrn, is_verified) VALUES
(2, 'ООО АвтоЗапчасти', '7701234567', '1027700132195', 1);

-- Демо-объявления
INSERT INTO listings (user_id, category_id, brand_id, type, title, slug, description, sku, barcode, price, old_price, discount_pct, quantity, status, has_warranty, warranty_text, published_at) VALUES
(2, 6, 3, 'product', 'Тормозные колодки Bosch передние BMW X5', 'tormoznye-kolodki-bosch-perednie-bmw-x5', 'Оригинальные тормозные колодки Bosch для BMW X5 E70. Высокое качество, гарантия 12 месяцев.', 'BP1234', '4601234567890', 4500, 5500, 18, 15, 'active', 1, '12 месяцев', NOW()),
(2, 8, 1, 'product', 'iPhone 15 Pro 256GB Natural Titanium', 'iphone-15-pro-256gb-natural-titanium', 'Новый iPhone 15 Pro, запечатанная коробка. Официальная гарантия Apple.', 'IP15P-256-NT', '0194253401234', 119990, 129990, 8, 5, 'active', 1, 'Apple 1 год', NOW()),
(2, 6, 3, 'product', 'Масляный фильтр Bosch для Lada Vesta', 'maslyanyj-filtr-bosch-dlya-lada-vesta', 'Масляный фильтр Bosch P 3274. Совместим с Lada Vesta, Granta.', 'P3274', '4609876543210', 450, NULL, NULL, 50, 'active', 0, NULL, NOW()),
(2, 3, NULL, 'service', 'Диагностика автомобиля компьютерная', 'diagnostika-avtomobilya-kompyuternaya', 'Полная компьютерная диагностика всех систем автомобиля. Запись по времени.', NULL, NULL, 2500, NULL, NULL, 999, 'active', 0, NULL, NOW());

INSERT INTO listing_car_compat (listing_id, make_id, model_id, year_from, year_to, aggregate) VALUES
(1, 1, 1, 2007, 2013, 'Передние тормоза'),
(3, 4, 3, 2015, 2024, 'Двигатель');

INSERT INTO listing_images (listing_id, path, sort_order) VALUES
(1, 'https://via.placeholder.com/400x300/2563eb/ffffff?text=Bosch+Brakes', 0),
(2, 'https://via.placeholder.com/400x300/1e293b/ffffff?text=iPhone+15+Pro', 0),
(3, 'https://via.placeholder.com/400x300/22c55e/ffffff?text=Oil+Filter', 0),
(4, 'https://via.placeholder.com/400x300/f59e0b/ffffff?text=Auto+Service', 0);
