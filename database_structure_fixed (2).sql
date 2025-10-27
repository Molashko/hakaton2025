-- ===============================
-- 🔹 Enum-типы
-- ===============================
CREATE TYPE user_status AS ENUM ('active', 'inactive');
CREATE TYPE order_type_settings AS ENUM ('ORDER_TYPE_1', 'ORDER_TYPE_2', 'ORDER_TYPE_3');
CREATE TYPE order_type_order AS ENUM ('ORDER_1', 'ORDER_2', 'ORDER_3');
CREATE TYPE order_status AS ENUM ('processed', 'await', 'accept', 'reject');

-- ===============================
-- 🔹 Таблица пользователей
-- ===============================
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255) NOT NULL,
    middle_name VARCHAR(255),
    role VARCHAR(50) NOT NULL DEFAULT 'executor',
    status user_status NOT NULL
);

CREATE INDEX idx_users_status ON users(status);

-- ===============================
-- 🔹 Таблица авторизации
-- ===============================
CREATE TABLE auth (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    username VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL
);

CREATE INDEX idx_auth_user_id ON auth(user_id);

-- ===============================
-- 🔹 Настройки пользователя
-- ===============================
CREATE TABLE user_settings (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE, 
    min_accept_sum BIGINT,
    max_accept_sum BIGINT,
    min_reject_sum BIGINT,
    max_reject_sum BIGINT,
    client_msp VARCHAR(255),
    executor_msp VARCHAR(255),
    order_type order_type_settings NOT NULL,
    subject UUID,
    vip BOOLEAN DEFAULT FALSE,
    max_daily_limit SMALLINT CHECK(max_daily_limit >= 0)
);

CREATE INDEX idx_user_settings_user_id ON user_settings(user_id);

-- ===============================
-- 🔹 Клиенты
-- ===============================
CREATE TABLE clients (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL
);

-- ===============================
-- 🔹 Таблица заявок
-- ===============================
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    parent_id INT REFERENCES orders(id) ON DELETE SET NULL,
    user_id INT REFERENCES users(id) ON DELETE SET NULL,
    executor_id INT REFERENCES users(id) ON DELETE SET NULL,
    client_id INT REFERENCES clients(id),
    sum BIGINT,
    client_msp VARCHAR(255),
    executor_msp VARCHAR(255),
    order_type order_type_order NOT NULL,
    subject UUID NOT NULL,
    vip BOOLEAN DEFAULT FALSE,
    description TEXT,
    status order_status NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TYPE order_status IS 'Статусы заявки: processed - в рассмотрении, await - на доработке, accept - решено, reject - отказано';

CREATE INDEX idx_order_user_id ON orders(user_id);
CREATE INDEX idx_order_parent_id ON orders(parent_id);
CREATE INDEX idx_order_status ON orders(status);
CREATE INDEX idx_order_subject ON orders(subject);

-- ===============================
-- 🔹 История изменений заявок
-- ===============================
CREATE TABLE order_history (
    id SERIAL PRIMARY KEY,
    order_id INT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    user_id INT REFERENCES users(id),
    old_status order_status,
    new_status order_status,
    comment TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_order_history_order_id ON order_history(order_id);
