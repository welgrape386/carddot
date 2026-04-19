-- =============================================
-- 카드 혜택 데이터베이스 스키마 
-- =============================================

-- 1. users (사용자 테이블)
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,                                    -- 사용자 고유 번호 (자동 증가)
    email VARCHAR(255) NOT NULL UNIQUE,                            -- 로그인/알림용 이메일 (중복 불가)
    password VARCHAR(255) NOT NULL,                                -- 암호화된 비밀번호 (bcrypt 등으로 해싱)
    name VARCHAR(50) NOT NULL,                                     -- 사용자 실명
    phone_number VARCHAR(20),                                      -- 휴대폰 번호 (선택)
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP        -- 가입 일시
);

-- 2. category (소비 카테고리 테이블)
CREATE TABLE category (
    category_id SERIAL PRIMARY KEY,                                -- 카테고리 고유 번호 (자동 증가)
    category_name VARCHAR(50) NOT NULL                             -- 카테고리명 (교통, 외식, 쇼핑 등)
);

-- 3. card (카드 기본 정보 테이블)
CREATE TABLE card (
    card_id VARCHAR(50) PRIMARY KEY,                               -- 카드 고유 ID (카드사에서 부여, 영문+숫자)
    card_name VARCHAR(100) NOT NULL,                               -- 카드 이름 (예: 신한카드 Deep Dream)
    company VARCHAR(50) NOT NULL,                                  -- 카드사 (신한, 삼성, 현대 등)
    card_type VARCHAR(10) NOT NULL,                                -- 카드 종류 (신용/체크)
    network VARCHAR(50),                                           -- 결제 네트워크 (VISA, Master, AMEX 등)
    is_domestic_foreign BOOLEAN NOT NULL DEFAULT FALSE,            -- 국내해외겸용 여부 (True: 해외겸용)
    has_transport BOOLEAN NOT NULL DEFAULT FALSE,                  -- 후불교통카드 기능 여부
    annual_fee_dom_basic INT NOT NULL DEFAULT 0,                   -- 국내 일반 연회비 (원)
    annual_fee_dom_premium INT NOT NULL DEFAULT 0,                 -- 국내 프리미엄 연회비 (원)
    annual_fee_for_basic INT NOT NULL DEFAULT 0,                   -- 해외 일반 연회비 (원)
    annual_fee_for_premium INT NOT NULL DEFAULT 0,                 -- 해외 프리미엄 연회비 (원)
    annual_fee_notes VARCHAR(255),                                 -- 연회비 관련 비고 (예: 전년 실적 충족 시 면제)
    min_performance INT NOT NULL DEFAULT 0,                        -- 기본 전월 실적 조건 (원)
    summary TEXT,                                                  -- 카드 대표 혜택 요약 (앱 메인에 노출)
    has_cashback BOOLEAN NOT NULL DEFAULT FALSE,                   -- 캐시백 이벤트 진행 중 여부
    image_url VARCHAR(500),                                        -- 카드 이미지 URL
    link_url VARCHAR(500),                                         -- 카드사 상세페이지 URL
    view_count INT NOT NULL DEFAULT 0,                             -- 앱 내 조회수 (인기순 정렬용)
    click_count INT NOT NULL DEFAULT 0,                            -- 카드사 URL 클릭수 (랭킹용 )
    total_max_benefit INT DEFAULT 0                                -- 월 최대 혜택 금액 (원)
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,       -- 최종 정보 갱신 일시
);

-- 4. benefit (카드 상세 혜택 테이블)
CREATE TABLE benefit (
    benefit_id       SERIAL          PRIMARY KEY,                  -- 혜택 고유 번호 (자동 증가)
    card_id          VARCHAR(50)     NOT NULL REFERENCES card(card_id), -- 어느 카드의 혜택인지 (FK)
    category_id      INT             REFERENCES category(category_id),  -- 혜택 카테고리 (FK, NULL 허용)
    benefit_group    VARCHAR(100)    NOT NULL,                     -- 혜택 그룹명
    benefit_type     VARCHAR(50),                                  -- 포인트적립 | 캐시백 | 할인 | 면제 | 서비스
    benefit_title    VARCHAR(255),                                 -- 혜택 소제목 (예: 건당 3만원 미만)
    benefit_content  TEXT,                                         -- 혜택 상세 내용 (원문)
    benefit_value    DECIMAL(10,2),                                -- 혜택 수치 (예: 0.70, 500.00)
    benefit_unit     VARCHAR(20),                                  -- % | 원 | 포인트 | 마일
    on_offline       VARCHAR(10),                                  -- Online | Offline | Both
    target_merchants   TEXT,                                       -- 적용 가맹점 목록 (쉼표 구분)
    excluded_merchants TEXT,                                       -- 제외 가맹점 목록 (쉼표 구분)
    performance_min  INT             DEFAULT 0,                    -- 이용금액 구간 하한
    performance_max  INT,                                          -- 이용금액 구간 상한 (NULL=상한없음)
    min_amount       INT,                                          -- 건당 최소 결제금액 (NULL=제한없음)
    max_count        INT,                                          -- 월 최대 혜택 횟수 (NULL=제한없음)
    max_limit        INT,                                          -- 월 최대 혜택 한도 수치
    max_limit_unit   VARCHAR(20),                                  -- 포인트 | 원 | 회
    benefit_notes    TEXT                                          -- 혜택 관련 유의사항
);

-- 5. card_event (카드 이벤트 테이블)
CREATE TABLE card_event (
    event_id SERIAL PRIMARY KEY,                                   -- 이벤트 고유 번호 (자동 증가)
    card_id VARCHAR(50) NOT NULL REFERENCES card(card_id),         -- 어느 카드의 이벤트인지 (FK)
    event_title VARCHAR(255) NOT NULL,                             -- 이벤트 제목
    start_date DATE,                                               -- 이벤트 시작일
    end_date DATE,                                                 -- 이벤트 종료일
    event_type VARCHAR(50),                                        -- 이벤트 유형 (캐시백, 할인, 포인트적립 등)
    section VARCHAR(100),                                          -- 이벤트 섹션/분류 (이벤트 요약 | 참여방법 | 유의사항 등)
    event_link VARCHAR(500),                                       -- 이벤트 상세페이지 URL
    event_content TEXT,                                            -- 이벤트 상세 내용
    event_notes TEXT,                                              -- 이벤트 유의사항
);

-- 6. card_notice (카드 유의사항 테이블)
CREATE TABLE card_notice (
    notice_id SERIAL PRIMARY KEY,                                  -- 유의사항 고유 번호 (자동 증가)
    card_id VARCHAR(50) NOT NULL REFERENCES card(card_id),         -- 어느 카드의 유의사항인지 (FK)
    notice_category VARCHAR(100),                                  -- 유의사항 대분류 (예: 필수안내사항)
    sub_category VARCHAR(100),                                     -- 유의사항 소분류
    notice_content TEXT NOT NULL,                                  -- 유의사항 원문 내용
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP                 -- 최종 갱신 일시
);

-- 7. favorite (즐겨찾기 테이블)
CREATE TABLE favorite (
    favorite_id SERIAL PRIMARY KEY,                                -- 즐겨찾기 고유 번호 (자동 증가)
    user_id INT NOT NULL REFERENCES users(user_id),                -- 즐겨찾기한 사용자 (FK)
    card_id VARCHAR(50) NOT NULL REFERENCES card(card_id),         -- 즐겨찾기한 카드 (FK)
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP        -- 즐겨찾기 등록 일시
);

-- 8. user_activity (사용자 활동 이력 테이블)
-- 명세서의 "최근 본 카드", "최근 비교한 카드" 기능 지원
CREATE TABLE user_activity (
    activity_id SERIAL PRIMARY KEY,                                -- 활동 고유 번호 (자동 증가)
    user_id INT NOT NULL REFERENCES users(user_id),                -- 활동한 사용자 (FK)
    card_id VARCHAR(50) REFERENCES card(card_id),                  -- 조회/비교한 카드 (FK, NULL 가능)
    type VARCHAR(50),                                              -- 활동 종류 (VIEW/URL_CLICK/COMPARE)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP                 -- 활동 발생 일시
);

-- 9. transactions (사용자 지출 내역 테이블)
CREATE TABLE transactions (
    transaction_id SERIAL PRIMARY KEY,                             -- 결제 건별 고유 번호 (자동 증가)
    user_id INT NOT NULL REFERENCES users(user_id),                -- 결제한 사용자 (FK)
    category_id INT REFERENCES category(category_id),              -- 결제 카테고리 (FK, NULL 가능)
    card_id VARCHAR(50) NOT NULL REFERENCES card(card_id),         -- 결제에 사용한 카드 (FK)
    merchant_name VARCHAR(100),                                    -- 가맹점명 (카테고리 추론용)
    amount INT NOT NULL,                                           -- 결제 금액 (원)
    approved_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP       -- 결제 승인 일시
);