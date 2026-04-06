-- ENUM 타입 정의
CREATE TYPE card_type AS ENUM ('credit', 'check');
CREATE TYPE benefit_type_enum AS ENUM ('discount', 'accumulate', 'etc');
CREATE TYPE unit_type AS ENUM ('%', '원', 'P');
CREATE TYPE on_offline_type AS ENUM ('online', 'offline', 'both');
CREATE TYPE activity_type AS ENUM ('VIEW', 'URL_CLICK', 'COMPARE');

-- (1) User
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    name VARCHAR(50) NOT NULL,
    nickname VARCHAR(50),
    phone_number VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

-- (2) Category
CREATE TABLE category (
    category_id SERIAL PRIMARY KEY,
    category_name VARCHAR(50) NOT NULL
);

-- (3) Card
CREATE TABLE card (
    card_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    company VARCHAR(50) NOT NULL,
    type card_type,
    network VARCHAR(30),
    has_transport BOOLEAN DEFAULT false,
    is_domestic_only BOOLEAN DEFAULT false,
    annual_fee_dom_basic INT DEFAULT 0,
    annual_fee_dom_premium INT DEFAULT 0,
    annual_fee_for_basic INT DEFAULT 0,
    annual_fee_for_premium INT DEFAULT 0,
    min_performance INT DEFAULT 0,
    summary TEXT,
    has_cashback BOOLEAN DEFAULT false,
    image_url VARCHAR(500),
    link_url VARCHAR(500),
    view_count INT DEFAULT 0,
    click_count INT DEFAULT 0,
    notes TEXT
);

-- (4) Benefit
CREATE TABLE benefit (
    benefit_id SERIAL PRIMARY KEY,
    card_id INT REFERENCES card(card_id) ON DELETE CASCADE,
    category_id INT REFERENCES category(category_id),
    title VARCHAR(200),
    benefit_type benefit_type_enum,
    value DECIMAL(10,2),
    unit unit_type,
    max_limit INT,
    on_offline on_offline_type,
    condition_text TEXT,
    target_merchants TEXT,
    excluded_merchants TEXT,
    performance_level INT,
    notes TEXT
);

-- (5) Card_Event
CREATE TABLE card_event (
    event_id SERIAL PRIMARY KEY,
    card_id INT REFERENCES card(card_id) ON DELETE CASCADE,
    title VARCHAR(200),
    period VARCHAR(100),
    link VARCHAR(500),
    content TEXT,
    notes TEXT
);

-- (6) User_Activity
CREATE TABLE user_activity (
    activity_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id) ON DELETE CASCADE,
    card_id INT REFERENCES card(card_id) ON DELETE CASCADE,
    type activity_type NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- (7) Transaction
CREATE TABLE transaction (
    transaction_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id) ON DELETE CASCADE,
    category_id INT REFERENCES category(category_id),
    card_id INT REFERENCES card(card_id),
    merchant_name VARCHAR(100),
    amount INT NOT NULL,
    approved_at TIMESTAMP DEFAULT NOW()
);