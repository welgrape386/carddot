-- =============================================
-- 카드 혜택 데이터베이스 스키마
-- =============================================

-- 1. users (회원 정보)
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,                      -- 로그인용 이메일
    password VARCHAR(255) NOT NULL,                          -- 암호화된 비밀번호
    name VARCHAR(50) NOT NULL,
    phone_number VARCHAR(20),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. category (소비 카테고리 22종)
CREATE TABLE category (
    category_id SERIAL PRIMARY KEY,
    category_name VARCHAR(50) NOT NULL
);

-- 3. card (카드 기본 정보)
CREATE TABLE card (
    card_id VARCHAR(50) PRIMARY KEY,                         -- 카드 고유 ID, 카드사마다 형식 다름
    card_name VARCHAR(100) NOT NULL,                         -- 카드 이름
    company VARCHAR(50) NOT NULL,                            -- 카드사명 (국민/삼성/신한/현대)
    card_type VARCHAR(10) NOT NULL,                          -- 신용/체크
    network VARCHAR(50),                                     -- VISA/AMEX/Local/Mastercard, 다중값 가능(쉼표구분)
    has_transport BOOLEAN NOT NULL DEFAULT FALSE,            -- true = 후불 교통카드 기능 있음
    is_domestic_foreign BOOLEAN NOT NULL DEFAULT FALSE,      -- true = 해외겸용, false = 국내전용
    annual_fee_dom_basic INT NOT NULL DEFAULT 0,             -- 국내 일반 연회비(원)
    annual_fee_dom_premium INT NOT NULL DEFAULT 0,           -- 국내 프리미엄 연회비(원)
    annual_fee_for_basic INT NOT NULL DEFAULT 0,             -- 해외 일반 연회비(원)
    annual_fee_for_premium INT NOT NULL DEFAULT 0,           -- 해외 프리미엄 연회비(원)
    annual_fee_notes VARCHAR(255),                           -- 연회비 관련 비고
    min_performance INT NOT NULL DEFAULT 0,                  -- 최소 전월 실적 조건(원)
    summary TEXT,                                            -- 카드 대표 혜택 요약, 앱 카드 목록에 노출 (구분자 |)
    has_cashback BOOLEAN NOT NULL DEFAULT FALSE,             -- true = 현재 캐시백 이벤트 진행중
    image_url VARCHAR(500),                                  -- 카드 이미지 URL
    link_url VARCHAR(500),                                   -- 카드 상세페이지 URL
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, -- 크롤링한 시점
    fee_content TEXT                                         -- 연회비 전체 내용
);

-- 4. card_stats (조회수/클릭수 통계, card에서 분리)
CREATE TABLE card_stats (
    card_id VARCHAR(50) PRIMARY KEY REFERENCES card(card_id),
    detail_click INT NOT NULL DEFAULT 0,                     -- 앱 내 카드 상세 조회수, 인기순 정렬에 사용
    url_click INT NOT NULL DEFAULT 0,                        -- 카드사 URL 클릭수, 랭킹 보조 지표
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 5. benefit (카드 상세 혜택)
CREATE TABLE benefit (
    benefit_id VARCHAR(50) PRIMARY KEY,                      -- 혜택 고유 ID, card_id + B0001 형식
    card_id VARCHAR(50) NOT NULL REFERENCES card(card_id),   -- 어떤 카드의 혜택인지
    row_type VARCHAR(20) NOT NULL,                           -- 주요혜택(소비 카테고리 기준) | 안내(소비카테고리와 관련없는 혜택&서비스)
    benefit_group VARCHAR(100),                              -- 혜택 그룹명
    benefit_type VARCHAR(50),                                -- 포인트 | 캐시백 | 할인 | 서비스 | 마일리지
    benefit_value DECIMAL(10,2),                             -- 혜택 수치. 예: 1.5(1.5%), 500.00(500원)
    benefit_unit VARCHAR(20),                                -- %/원/포인트/마일리지, benefit_value와 함께 해석
    on_offline VARCHAR(10),                                  -- Online/Offline/Both
    target_merchants TEXT,                                   -- 할인 대상(업종 포함)
    performance_level TEXT,                                  -- 이용 조건 구간 텍스트. 예: 전월 30만원 이상 60만원 미만
    performance_min INT DEFAULT 0,                           -- 이용 조건 최소 금액(원)
    performance_max INT,                                     -- 이용 조건 최대 금액(원), null = 상한없음(무제한)
    min_amount INT,                                          -- 건당 최소 결제 금액(원), null = 제한없음
    max_count VARCHAR(50),                                   -- 월 최대 혜택 횟수, null = 횟수 무제한
    max_limit INT,                                           -- 월 최대 혜택 한도 수치, null = 한도없음
    max_limit_unit VARCHAR(20),                              -- 월 최대 혜택 한도 단위(원/포인트 등)
    group_max_limit INT,                                     -- 같은 benefit_group 내 여러 혜택이 공유하는 통합 월 한도 금액(원단위 정수)
    group_max_limit_unit VARCHAR(20),                        -- 통합 월 한도 단위(원/포인트/마일리지)
    unit_amount INT,                                         -- "N원당 M마일/포인트"에서 N(적립 기준금액), 알고리즘용
    ui_title TEXT,                                           -- 단일 카드 조회에서 혜택내용에 해당하는 텍스트
    ui_content TEXT                                          -- 고객에게 보여줄 상세 내용 (ui_title의 토글)
);

-- 6. benefit_category (혜택-카테고리 매핑)
CREATE TABLE benefit_category (
    benefit_id VARCHAR(50) NOT NULL REFERENCES benefit(benefit_id),
    category_id INT NOT NULL REFERENCES category(category_id),
    PRIMARY KEY (benefit_id, category_id)
);

-- 7. notice (카드 기본 유의사항, 카드 1개당 단일 행)
CREATE TABLE notice (
    notice_id SERIAL PRIMARY KEY,
    card_id VARCHAR(50) NOT NULL REFERENCES card(card_id),
    notice_content TEXT NOT NULL                             -- 유의사항 내용들
);

-- 8. card_event (카드 이벤트, section별 행)
CREATE TABLE card_event (
    id SERIAL PRIMARY KEY,                                   -- 행 구분용 pk
    event_id VARCHAR(50) NOT NULL DEFAULT '',                -- card_id+E0001, 같은 이벤트 그룹키
    card_id VARCHAR(50) NOT NULL REFERENCES card(card_id),
    event_title VARCHAR(255) NOT NULL,
    event_link VARCHAR(500),
    start_date DATE,                                         -- null = 상시 이벤트
    end_date DATE,                                           -- null = 종료일 미정
    event_type VARCHAR(50),                                  -- 캐시백/포인트/할인/서비스/기타
    section VARCHAR(100),                                    -- 내용/대상/혜택제공/확인사항 등 (확인사항만 통일 )
    event_content TEXT
);

-- 9. dev_cards (개발자용 혜택 데이터)
CREATE TABLE dev_cards (
    dev_id SERIAL PRIMARY KEY,
    benefit_group VARCHAR(255),                              -- 예: "M포인트 적립"
    benefit_title VARCHAR(255),                              -- 예: "기본 혜택"
    benefit_content TEXT
);

-- 10. user_compare_history (카드 비교 이력)
CREATE TABLE user_compare_history (
    compare_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id),      -- 사용자 
    card_id_1 VARCHAR(50) NOT NULL REFERENCES card(card_id),-- 비교 대상 카드1
    card_id_2 VARCHAR(50) NOT NULL REFERENCES card(card_id),-- 비교 대상 카드2
    card_id_3 VARCHAR(50) REFERENCES card(card_id),         -- 비교 대상 카드3(선택, 2개만 비교시 null값)
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 11. user_activity (최근 본 카드 / URL 클릭 / 비교 이력)
CREATE TABLE user_activity (
    activity_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(user_id),
    card_id VARCHAR(50) REFERENCES card(card_id),
    type VARCHAR(50),                                        -- VIEW/URL_CLICK/COMPARE
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);