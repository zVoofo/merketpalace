-- ============================================================
-- Торговая площадка (Доска объявлений) — полная схема БД
-- MySQL 8.0+ / MariaDB 10.5+
-- ============================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE DATABASE IF NOT EXISTS marketplace
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE marketplace;

-- ------------------------------------------------------------
-- РОЛИ И ПОЛЬЗОВАТЕЛИ
-- ------------------------------------------------------------

CREATE TABLE roles (
    id          TINYINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    code        VARCHAR(32)  NOT NULL UNIQUE,
    name        VARCHAR(64)  NOT NULL,
    description VARCHAR(255) NULL
) ENGINE=InnoDB;

INSERT INTO roles (code, name, description) VALUES
    ('guest',     'Гость',              'Неавторизованный пользователь'),
    ('buyer',     'Покупатель',         'Физическое лицо — покупатель'),
    ('buyer_org', 'Покупатель (Орг.)',  'Юридическое лицо — покупатель'),
    ('seller',    'Продавец',           'Частное лицо / компания — продавец'),
    ('manager',   'Менеджер продавца',  'Менеджер магазина продавца'),
    ('admin',     'Администратор',      'Полный доступ к системе');

CREATE TABLE users (
    id              BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    email           VARCHAR(255) NULL UNIQUE,
    phone           VARCHAR(20)  NULL UNIQUE,
    password_hash   VARCHAR(255) NULL,
    first_name      VARCHAR(100) NULL,
    last_name       VARCHAR(100) NULL,
    avatar          VARCHAR(500) NULL,
    active_role     ENUM('buyer','seller') NOT NULL DEFAULT 'buyer',
    is_verified     TINYINT(1) NOT NULL DEFAULT 0,
    is_blocked      TINYINT(1) NOT NULL DEFAULT 0,
    email_verified  TINYINT(1) NOT NULL DEFAULT 0,
    phone_verified  TINYINT(1) NOT NULL DEFAULT 0,
    last_login_at   DATETIME NULL,
    last_login_ip   VARCHAR(45) NULL,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_users_active (is_blocked, active_role)
) ENGINE=InnoDB;

CREATE TABLE user_roles (
    user_id BIGINT UNSIGNED NOT NULL,
    role_id TINYINT UNSIGNED NOT NULL,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE organizations (
    id          BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    user_id     BIGINT UNSIGNED NOT NULL UNIQUE,
    name        VARCHAR(255) NOT NULL,
    inn         VARCHAR(12)  NULL,
    ogrn        VARCHAR(15)  NULL,
    kpp         VARCHAR(9)   NULL,
    legal_address TEXT NULL,
    logo        VARCHAR(500) NULL,
    is_verified TINYINT(1) NOT NULL DEFAULT 0,
    verified_at DATETIME NULL,
    verified_by BIGINT UNSIGNED NULL,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE social_accounts (
    id            BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    user_id       BIGINT UNSIGNED NOT NULL,
    provider      ENUM('vk','google','apple') NOT NULL,
    provider_id   VARCHAR(255) NOT NULL,
    access_token  TEXT NULL,
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_provider (provider, provider_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE sms_codes (
    id         BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    phone      VARCHAR(20) NOT NULL,
    code       VARCHAR(6)  NOT NULL,
    purpose    ENUM('login','register','reset') NOT NULL DEFAULT 'login',
    expires_at DATETIME NOT NULL,
    used       TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_sms_phone (phone, used, expires_at)
) ENGINE=InnoDB;

CREATE TABLE password_resets (
    id         BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    email      VARCHAR(255) NOT NULL,
    token      VARCHAR(64) NOT NULL UNIQUE,
    expires_at DATETIME NOT NULL,
    used       TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE user_sessions (
    id         VARCHAR(64) PRIMARY KEY,
    user_id    BIGINT UNSIGNED NOT NULL,
    ip_address VARCHAR(45) NULL,
    user_agent TEXT NULL,
    expires_at DATETIME NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE activity_logs (
    id         BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    user_id    BIGINT UNSIGNED NULL,
    action     VARCHAR(100) NOT NULL,
    entity     VARCHAR(50)  NULL,
    entity_id  BIGINT UNSIGNED NULL,
    ip_address VARCHAR(45) NULL,
    user_agent TEXT NULL,
    meta       JSON NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_logs_user (user_id, created_at),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- СПРАВОЧНИКИ И КАТЕГОРИИ
-- ------------------------------------------------------------

CREATE TABLE categories (
    id          INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    parent_id   INT UNSIGNED NULL,
    slug        VARCHAR(150) NOT NULL UNIQUE,
    name        VARCHAR(255) NOT NULL,
    description TEXT NULL,
    icon        VARCHAR(100) NULL,
    sort_order  INT NOT NULL DEFAULT 0,
    is_active   TINYINT(1) NOT NULL DEFAULT 1,
    FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE SET NULL,
    INDEX idx_cat_parent (parent_id, sort_order)
) ENGINE=InnoDB;

CREATE TABLE brands (
    id         INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    name       VARCHAR(150) NOT NULL UNIQUE,
    slug       VARCHAR(150) NOT NULL UNIQUE,
    logo       VARCHAR(500) NULL,
    is_active  TINYINT(1) NOT NULL DEFAULT 1
) ENGINE=InnoDB;

CREATE TABLE attributes (
    id          INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    code        VARCHAR(50) NOT NULL UNIQUE,
    name        VARCHAR(150) NOT NULL,
    type        ENUM('text','number','select','boolean','color') NOT NULL DEFAULT 'text',
    unit        VARCHAR(20) NULL,
    is_filterable TINYINT(1) NOT NULL DEFAULT 1
) ENGINE=InnoDB;

CREATE TABLE category_attributes (
    category_id  INT UNSIGNED NOT NULL,
    attribute_id INT UNSIGNED NOT NULL,
    is_required  TINYINT(1) NOT NULL DEFAULT 0,
    sort_order   INT NOT NULL DEFAULT 0,
    PRIMARY KEY (category_id, attribute_id),
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
    FOREIGN KEY (attribute_id) REFERENCES attributes(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Авто-справочник (VIN / марка-модель)
CREATE TABLE car_makes (
    id   INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE car_models (
    id      INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    make_id INT UNSIGNED NOT NULL,
    name    VARCHAR(100) NOT NULL,
    FOREIGN KEY (make_id) REFERENCES car_makes(id) ON DELETE CASCADE,
    UNIQUE KEY uk_make_model (make_id, name)
) ENGINE=InnoDB;

CREATE TABLE car_years (
    id       INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    model_id INT UNSIGNED NOT NULL,
    year_from SMALLINT NOT NULL,
    year_to   SMALLINT NULL,
    FOREIGN KEY (model_id) REFERENCES car_models(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- ОБЪЯВЛЕНИЯ / ТОВАРЫ / УСЛУГИ
-- ------------------------------------------------------------

CREATE TABLE listings (
    id              BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    user_id         BIGINT UNSIGNED NOT NULL,
    category_id     INT UNSIGNED NOT NULL,
    brand_id        INT UNSIGNED NULL,
    type            ENUM('product','service') NOT NULL DEFAULT 'product',
    title           VARCHAR(300) NOT NULL,
    slug            VARCHAR(350) NOT NULL,
    description     TEXT NULL,
    sku             VARCHAR(100) NULL,
    barcode         VARCHAR(50)  NULL,
    price           DECIMAL(12,2) NOT NULL DEFAULT 0,
    old_price       DECIMAL(12,2) NULL,
    discount_pct    TINYINT UNSIGNED NULL,
    price_unit      ENUM('piece','pack','hour','service') NOT NULL DEFAULT 'piece',
    currency        CHAR(3) NOT NULL DEFAULT 'RUB',
    quantity        INT NOT NULL DEFAULT 0,
    status          ENUM('draft','pending','active','rejected','archived','out_of_stock','on_order') NOT NULL DEFAULT 'draft',
    condition_type  ENUM('new','used','refurbished') NOT NULL DEFAULT 'new',
    has_warranty    TINYINT(1) NOT NULL DEFAULT 0,
    warranty_text   VARCHAR(500) NULL,
    return_policy   TEXT NULL,
    views_count     INT UNSIGNED NOT NULL DEFAULT 0,
    chat_clicks     INT UNSIGNED NOT NULL DEFAULT 0,
    sales_count     INT UNSIGNED NOT NULL DEFAULT 0,
    rating_avg      DECIMAL(3,2) NOT NULL DEFAULT 0,
    rating_count    INT UNSIGNED NOT NULL DEFAULT 0,
    moderation_note TEXT NULL,
    moderated_at    DATETIME NULL,
    moderated_by    BIGINT UNSIGNED NULL,
    published_at    DATETIME NULL,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FULLTEXT INDEX ft_listings (title, description, sku, barcode),
    INDEX idx_listings_status (status, published_at),
    INDEX idx_listings_user (user_id, status),
    INDEX idx_listings_category (category_id, status),
    INDEX idx_listings_sku (sku),
    INDEX idx_listings_barcode (barcode),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(id),
    FOREIGN KEY (brand_id) REFERENCES brands(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE listing_images (
    id          BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    listing_id  BIGINT UNSIGNED NOT NULL,
    path        VARCHAR(500) NOT NULL,
    is_video    TINYINT(1) NOT NULL DEFAULT 0,
    sort_order  INT NOT NULL DEFAULT 0,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE listing_attributes (
    listing_id   BIGINT UNSIGNED NOT NULL,
    attribute_id INT UNSIGNED NOT NULL,
    value        VARCHAR(500) NOT NULL,
    PRIMARY KEY (listing_id, attribute_id),
    FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE,
    FOREIGN KEY (attribute_id) REFERENCES attributes(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE listing_car_compat (
    listing_id BIGINT UNSIGNED NOT NULL,
    make_id    INT UNSIGNED NOT NULL,
    model_id   INT UNSIGNED NULL,
    year_from  SMALLINT NULL,
    year_to    SMALLINT NULL,
    aggregate  VARCHAR(100) NULL,
    PRIMARY KEY (listing_id, make_id, model_id),
    FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE,
    FOREIGN KEY (make_id) REFERENCES car_makes(id),
    FOREIGN KEY (model_id) REFERENCES car_models(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- Календарь услуг
CREATE TABLE service_slots (
    id          BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    listing_id  BIGINT UNSIGNED NOT NULL,
    slot_date   DATE NOT NULL,
    time_from   TIME NOT NULL,
    time_to     TIME NOT NULL,
    is_booked   TINYINT(1) NOT NULL DEFAULT 0,
    FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE,
    INDEX idx_slots (listing_id, slot_date, is_booked)
) ENGINE=InnoDB;

-- Склад / интеграции
CREATE TABLE warehouses (
    id          INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    user_id     BIGINT UNSIGNED NOT NULL,
    name        VARCHAR(150) NOT NULL,
    address     TEXT NULL,
    external_id VARCHAR(100) NULL,
    provider    ENUM('manual','1c','moysklad','other') NOT NULL DEFAULT 'manual',
    api_config  JSON NULL,
    is_active   TINYINT(1) NOT NULL DEFAULT 1,
    last_sync   DATETIME NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE warehouse_stock (
    warehouse_id INT UNSIGNED NOT NULL,
    listing_id   BIGINT UNSIGNED NOT NULL,
    quantity     INT NOT NULL DEFAULT 0,
    reserved     INT NOT NULL DEFAULT 0,
    updated_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (warehouse_id, listing_id),
    FOREIGN KEY (warehouse_id) REFERENCES warehouses(id) ON DELETE CASCADE,
    FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE stock_sync_log (
    id           BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    warehouse_id INT UNSIGNED NOT NULL,
    status       ENUM('success','error') NOT NULL,
    items_synced INT NOT NULL DEFAULT 0,
    error_msg    TEXT NULL,
    created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (warehouse_id) REFERENCES warehouses(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- ПОИСК И АНАЛИТИКА
-- ------------------------------------------------------------

CREATE TABLE search_queries (
    id           BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    user_id      BIGINT UNSIGNED NULL,
    query        VARCHAR(500) NOT NULL,
    results_count INT NOT NULL DEFAULT 0,
    filters      JSON NULL,
    ip_address   VARCHAR(45) NULL,
    created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_search_query (query(100)),
    INDEX idx_search_zero (results_count, created_at),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE search_requests (
    id          BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    user_id     BIGINT UNSIGNED NULL,
    query       VARCHAR(500) NOT NULL,
    description TEXT NULL,
    contact     VARCHAR(100) NULL,
    status      ENUM('new','in_progress','found','closed') NOT NULL DEFAULT 'new',
    assigned_to BIGINT UNSIGNED NULL,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE listing_views (
    id         BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    listing_id BIGINT UNSIGNED NOT NULL,
    user_id    BIGINT UNSIGNED NULL,
    ip_address VARCHAR(45) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_views_listing (listing_id, created_at),
    FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- КОРЗИНА И ЗАКАЗЫ
-- ------------------------------------------------------------

CREATE TABLE carts (
    id         BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    user_id    BIGINT UNSIGNED NULL,
    session_id VARCHAR(64) NULL,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_cart_user (user_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE cart_items (
    id         BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    cart_id    BIGINT UNSIGNED NOT NULL,
    listing_id BIGINT UNSIGNED NOT NULL,
    quantity   INT NOT NULL DEFAULT 1,
    price      DECIMAL(12,2) NOT NULL,
    UNIQUE KEY uk_cart_listing (cart_id, listing_id),
    FOREIGN KEY (cart_id) REFERENCES carts(id) ON DELETE CASCADE,
    FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE orders (
    id              BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    order_number    VARCHAR(20) NOT NULL UNIQUE,
    buyer_id        BIGINT UNSIGNED NOT NULL,
    seller_id       BIGINT UNSIGNED NOT NULL,
    buyer_type      ENUM('individual','organization') NOT NULL DEFAULT 'individual',
    status          ENUM('pending','paid','processing','shipped','delivered','completed','cancelled','disputed') NOT NULL DEFAULT 'pending',
    subtotal        DECIMAL(12,2) NOT NULL,
    delivery_cost   DECIMAL(12,2) NOT NULL DEFAULT 0,
    total           DECIMAL(12,2) NOT NULL,
    delivery_type   ENUM('courier','pickup','transport','service_location') NULL,
    delivery_address TEXT NULL,
    payment_method  ENUM('card','wallet','postpay','escrow') NULL,
    payment_status  ENUM('pending','paid','held','released','refunded') NOT NULL DEFAULT 'pending',
    escrow_held     TINYINT(1) NOT NULL DEFAULT 0,
    org_details     JSON NULL,
    notes           TEXT NULL,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_orders_buyer (buyer_id, status),
    INDEX idx_orders_seller (seller_id, status),
    FOREIGN KEY (buyer_id) REFERENCES users(id),
    FOREIGN KEY (seller_id) REFERENCES users(id)
) ENGINE=InnoDB;

CREATE TABLE order_items (
    id         BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    order_id   BIGINT UNSIGNED NOT NULL,
    listing_id BIGINT UNSIGNED NOT NULL,
    title      VARCHAR(300) NOT NULL,
    quantity   INT NOT NULL,
    price      DECIMAL(12,2) NOT NULL,
    total      DECIMAL(12,2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (listing_id) REFERENCES listings(id)
) ENGINE=InnoDB;

CREATE TABLE order_documents (
    id         BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    order_id   BIGINT UNSIGNED NOT NULL,
    type       ENUM('receipt','contract','act','invoice') NOT NULL,
    file_path  VARCHAR(500) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE payments (
    id              BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    order_id        BIGINT UNSIGNED NOT NULL,
    gateway         ENUM('yukassa','stripe','tinkoff') NOT NULL,
    external_id     VARCHAR(100) NULL,
    amount          DECIMAL(12,2) NOT NULL,
    status          ENUM('pending','success','failed','refunded') NOT NULL DEFAULT 'pending',
    gateway_response JSON NULL,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- КОММУНИКАЦИИ
-- ------------------------------------------------------------

CREATE TABLE conversations (
    id          BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    listing_id  BIGINT UNSIGNED NOT NULL,
    buyer_id    BIGINT UNSIGNED NOT NULL,
    seller_id   BIGINT UNSIGNED NOT NULL,
    last_msg_at DATETIME NULL,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_conv (listing_id, buyer_id, seller_id),
    FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE,
    FOREIGN KEY (buyer_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (seller_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE messages (
    id              BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    conversation_id BIGINT UNSIGNED NOT NULL,
    sender_id       BIGINT UNSIGNED NOT NULL,
    body            TEXT NULL,
    attachment_path VARCHAR(500) NULL,
    attachment_type ENUM('image','video','document') NULL,
    is_read         TINYINT(1) NOT NULL DEFAULT 0,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_messages_conv (conversation_id, created_at),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE message_templates (
    id      INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    title   VARCHAR(100) NOT NULL,
    body    TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- ОТЗЫВЫ И РЕЙТИНГ
-- ------------------------------------------------------------

CREATE TABLE reviews (
    id          BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    order_id    BIGINT UNSIGNED NULL,
    listing_id  BIGINT UNSIGNED NOT NULL,
    reviewer_id BIGINT UNSIGNED NOT NULL,
    seller_id   BIGINT UNSIGNED NOT NULL,
    rating      TINYINT UNSIGNED NOT NULL CHECK (rating BETWEEN 1 AND 5),
    text        TEXT NULL,
    status      ENUM('pending','approved','rejected') NOT NULL DEFAULT 'pending',
    seller_reply TEXT NULL,
    replied_at  DATETIME NULL,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_reviews_listing (listing_id, status),
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE SET NULL,
    FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE,
    FOREIGN KEY (reviewer_id) REFERENCES users(id),
    FOREIGN KEY (seller_id) REFERENCES users(id)
) ENGINE=InnoDB;

CREATE TABLE review_comments (
    id         BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    review_id  BIGINT UNSIGNED NOT NULL,
    user_id    BIGINT UNSIGNED NOT NULL,
    text       TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (review_id) REFERENCES reviews(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- УВЕДОМЛЕНИЯ
-- ------------------------------------------------------------

CREATE TABLE notifications (
    id         BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    user_id    BIGINT UNSIGNED NOT NULL,
    type       VARCHAR(50) NOT NULL,
    title      VARCHAR(255) NOT NULL,
    body       TEXT NULL,
    link       VARCHAR(500) NULL,
    is_read    TINYINT(1) NOT NULL DEFAULT 0,
    channel    ENUM('push','email','sms','in_app') NOT NULL DEFAULT 'in_app',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_notif_user (user_id, is_read),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- АДМИНИСТРИРОВАНИЕ
-- ------------------------------------------------------------

CREATE TABLE stop_words (
    id   INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    word VARCHAR(100) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE moderation_queue (
    id          BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    entity_type ENUM('listing','review','user') NOT NULL,
    entity_id   BIGINT UNSIGNED NOT NULL,
    reason      VARCHAR(255) NULL,
    status      ENUM('pending','approved','rejected') NOT NULL DEFAULT 'pending',
    moderator_id BIGINT UNSIGNED NULL,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at DATETIME NULL
) ENGINE=InnoDB;

CREATE TABLE seller_payouts (
    id          BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    seller_id   BIGINT UNSIGNED NOT NULL,
    amount      DECIMAL(12,2) NOT NULL,
    commission  DECIMAL(12,2) NOT NULL DEFAULT 0,
    status      ENUM('pending','processing','paid','rejected') NOT NULL DEFAULT 'pending',
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    paid_at     DATETIME NULL,
    FOREIGN KEY (seller_id) REFERENCES users(id)
) ENGINE=InnoDB;

CREATE TABLE email_campaigns (
    id          INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    title       VARCHAR(255) NOT NULL,
    subject     VARCHAR(255) NOT NULL,
    body        TEXT NOT NULL,
    segment     JSON NULL,
    status      ENUM('draft','scheduled','sent') NOT NULL DEFAULT 'draft',
    sent_count  INT NOT NULL DEFAULT 0,
    created_by  BIGINT UNSIGNED NULL,
    sent_at     DATETIME NULL,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- НАЧАЛЬНЫЕ ДАННЫЕ
-- ------------------------------------------------------------

INSERT INTO categories (parent_id, slug, name, sort_order) VALUES
    (NULL, 'avto', 'Авто и запчасти', 1),
    (NULL, 'elektronika', 'Электроника', 2),
    (NULL, 'uslugi', 'Услуги', 3),
    (NULL, 'dom', 'Дом и сад', 4),
    (NULL, 'odezhda', 'Одежда', 5);

INSERT INTO categories (parent_id, slug, name, sort_order) VALUES
    (1, 'zapchasti', 'Запчасти', 1),
    (1, 'shiny-diski', 'Шины и диски', 2),
    (2, 'telefony', 'Телефоны', 1),
    (2, 'kompyutery', 'Компьютеры', 2);

INSERT INTO attributes (code, name, type, is_filterable) VALUES
    ('color', 'Цвет', 'color', 1),
    ('size', 'Размер', 'select', 1),
    ('weight', 'Вес', 'number', 0),
    ('material', 'Материал', 'text', 1);

INSERT INTO brands (name, slug) VALUES
    ('Apple', 'apple'),
    ('Samsung', 'samsung'),
    ('Bosch', 'bosch'),
    ('BMW', 'bmw');

INSERT INTO car_makes (name) VALUES ('BMW'), ('Mercedes-Benz'), ('Toyota'), ('Lada');
INSERT INTO car_models (make_id, name) VALUES (1, 'X5'), (1, '3 Series'), (4, 'Vesta'), (4, 'Granta');

INSERT INTO stop_words (word) VALUES ('наркотик'), ('оружие'), ('подделка');

-- Администратор (пароль задаётся в install.php: admin123)
INSERT INTO users (email, password_hash, first_name, last_name, active_role, is_verified, email_verified)
VALUES ('admin@marketplace.local', '$2y$10$placeholder', 'Админ', 'Системы', 'buyer', 1, 1);

INSERT INTO user_roles (user_id, role_id) VALUES (1, 6);

SET FOREIGN_KEY_CHECKS = 1;
