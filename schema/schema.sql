-- ============================================================================
-- AI-POWERED PERSONAL EXPENSE MANAGER — COMPLETE DATABASE SCHEMA
-- ============================================================================
-- Database   : PostgreSQL (recommended) / SQLite (dev fallback)
-- Created    : 2026-02-23
-- Description: Covers Authentication, Expense Storage, Chatbot, Automation,
--              Security, AI Recommendations, Dashboard Analytics, OCR/Receipt
--              Processing, Bill Splitting, and Notification modules.
-- ============================================================================

-- ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
-- 0. EXTENSIONS (PostgreSQL only — skip for SQLite)
-- ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";          -- UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";           -- Encryption helpers


-- ############################################################################
-- MODULE 1 — AUTHENTICATION & USER MANAGEMENT
-- ############################################################################

-- 1.1  Users
CREATE TABLE users (
    user_id             UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    email               VARCHAR(255)    NOT NULL UNIQUE,
    password_hash       VARCHAR(512)    NOT NULL,           -- bcrypt / argon2
    full_name           VARCHAR(150)    NOT NULL,
    phone_number        VARCHAR(20),
    profile_picture_url TEXT,
    preferred_currency  VARCHAR(10)     NOT NULL DEFAULT 'INR',
    locale              VARCHAR(10)     NOT NULL DEFAULT 'en-IN',
    timezone            VARCHAR(50)     NOT NULL DEFAULT 'Asia/Kolkata',
    is_active           BOOLEAN         NOT NULL DEFAULT TRUE,
    is_verified         BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users (email);

-- 1.2  OAuth / Social Login Providers
CREATE TABLE oauth_providers (
    oauth_id            UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID            NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    provider_name       VARCHAR(50)     NOT NULL,           -- 'google', 'github', 'facebook'
    provider_user_id    VARCHAR(255)    NOT NULL,
    access_token        TEXT,                                -- encrypted at rest
    refresh_token       TEXT,                                -- encrypted at rest
    token_expires_at    TIMESTAMPTZ,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    UNIQUE (provider_name, provider_user_id)
);

CREATE INDEX idx_oauth_user ON oauth_providers (user_id);

-- 1.3  Sessions / Refresh Tokens
CREATE TABLE sessions (
    session_id          UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID            NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    refresh_token_hash  VARCHAR(512)    NOT NULL,
    device_info         JSONB,                               -- user-agent, IP, etc.
    ip_address          INET,
    is_revoked          BOOLEAN         NOT NULL DEFAULT FALSE,
    expires_at          TIMESTAMPTZ     NOT NULL,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sessions_user   ON sessions (user_id);
CREATE INDEX idx_sessions_expiry ON sessions (expires_at);

-- 1.4  Password Reset Tokens
CREATE TABLE password_reset_tokens (
    token_id            UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID            NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    token_hash          VARCHAR(512)    NOT NULL,
    expires_at          TIMESTAMPTZ     NOT NULL,
    is_used             BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- 1.5  Email Verification Tokens
CREATE TABLE email_verification_tokens (
    token_id            UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID            NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    token_hash          VARCHAR(512)    NOT NULL,
    expires_at          TIMESTAMPTZ     NOT NULL,
    is_used             BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);


-- ############################################################################
-- MODULE 2 — PRIVACY, CONSENT & ACCESS CONTROL
-- ############################################################################

-- 2.1  Roles
CREATE TABLE roles (
    role_id             SERIAL          PRIMARY KEY,
    role_name           VARCHAR(50)     NOT NULL UNIQUE,     -- 'user', 'admin', 'premium'
    description         TEXT,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

INSERT INTO roles (role_name, description) VALUES
    ('user',    'Standard free-tier user'),
    ('premium', 'Premium subscription user'),
    ('admin',   'System administrator');

-- 2.2  User ↔ Role Mapping
CREATE TABLE user_roles (
    user_id             UUID            NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    role_id             INT             NOT NULL REFERENCES roles (role_id) ON DELETE CASCADE,
    assigned_at         TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    PRIMARY KEY (user_id, role_id)
);

-- 2.3  Privacy & Consent Preferences
CREATE TABLE user_privacy_settings (
    setting_id          UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID            NOT NULL UNIQUE REFERENCES users (user_id) ON DELETE CASCADE,
    allow_analytics     BOOLEAN         NOT NULL DEFAULT TRUE,
    allow_ai_training   BOOLEAN         NOT NULL DEFAULT FALSE,
    share_anonymous_data BOOLEAN        NOT NULL DEFAULT FALSE,
    data_retention_days INT             NOT NULL DEFAULT 365,   -- how long to keep data
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- 2.4  Consent Audit Log (GDPR / compliance)
CREATE TABLE consent_audit_log (
    log_id              UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID            NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    consent_type        VARCHAR(100)    NOT NULL,               -- 'analytics', 'ai_training', etc.
    action              VARCHAR(20)     NOT NULL,               -- 'granted', 'revoked'
    ip_address          INET,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- 2.5  Data Encryption Keys (per-user envelope encryption)
CREATE TABLE user_encryption_keys (
    key_id              UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID            NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    encrypted_dek       BYTEA           NOT NULL,               -- DEK encrypted by master KEK
    key_version         INT             NOT NULL DEFAULT 1,
    is_active           BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    rotated_at          TIMESTAMPTZ
);


-- ############################################################################
-- MODULE 3 — EXPENSE STORAGE ENGINE
-- ############################################################################

-- 3.1  Expense Categories (system + user-defined)
CREATE TABLE categories (
    category_id         SERIAL          PRIMARY KEY,
    user_id             UUID            REFERENCES users (user_id) ON DELETE CASCADE, -- NULL = system default
    name                VARCHAR(100)    NOT NULL,
    icon                VARCHAR(50),             -- emoji or icon-class name
    color               VARCHAR(7),              -- hex color code
    parent_category_id  INT             REFERENCES categories (category_id) ON DELETE SET NULL,
    is_system_default   BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_categories_user ON categories (user_id);

-- Seed system default categories
INSERT INTO categories (name, icon, color, is_system_default) VALUES
    ('Food & Dining',       '🍔', '#FF6B6B', TRUE),
    ('Groceries',           '🛒', '#4ECDC4', TRUE),
    ('Transportation',      '🚗', '#45B7D1', TRUE),
    ('Shopping',            '🛍️', '#96CEB4', TRUE),
    ('Entertainment',       '🎬', '#FFEAA7', TRUE),
    ('Bills & Utilities',   '💡', '#DDA0DD', TRUE),
    ('Healthcare',          '🏥', '#98D8C8', TRUE),
    ('Education',           '📚', '#F7DC6F', TRUE),
    ('Rent & Housing',      '🏠', '#BB8FCE', TRUE),
    ('Travel',              '✈️', '#85C1E9', TRUE),
    ('Personal Care',       '💇', '#F0B27A', TRUE),
    ('Subscriptions',       '📱', '#AED6F1', TRUE),
    ('Gifts & Donations',   '🎁', '#F5B7B1', TRUE),
    ('Investments',         '📈', '#82E0AA', TRUE),
    ('Miscellaneous',       '📌', '#D5DBDB', TRUE);

-- 3.2  Payment Methods
CREATE TABLE payment_methods (
    payment_method_id   SERIAL          PRIMARY KEY,
    user_id             UUID            NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    method_type         VARCHAR(50)     NOT NULL,            -- 'cash','upi','credit_card','debit_card','net_banking','wallet'
    label               VARCHAR(100)    NOT NULL,            -- 'HDFC Visa ****1234'
    provider            VARCHAR(100),                        -- 'HDFC Bank', 'Paytm', 'GPay'
    last_four_digits    VARCHAR(4),
    is_default          BOOLEAN         NOT NULL DEFAULT FALSE,
    is_active           BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_payment_methods_user ON payment_methods (user_id);

-- 3.3  Expenses (core table)
CREATE TABLE expenses (
    expense_id          UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID            NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    category_id         INT             REFERENCES categories (category_id) ON DELETE SET NULL,
    payment_method_id   INT             REFERENCES payment_methods (payment_method_id) ON DELETE SET NULL,
    amount              DECIMAL(15,2)   NOT NULL CHECK (amount > 0),
    currency            VARCHAR(10)     NOT NULL DEFAULT 'INR',
    description         TEXT,
    vendor_name         VARCHAR(255),
    expense_date        DATE            NOT NULL,
    expense_time        TIME,
    location            TEXT,
    latitude            DECIMAL(10,7),
    longitude           DECIMAL(10,7),
    tags                TEXT[],                              -- array of user-defined tags
    source              VARCHAR(50)     NOT NULL DEFAULT 'manual',
                                                             -- 'manual','chatbot','nlp','ocr','bank_import','email','recurring','voice'
    is_recurring        BOOLEAN         NOT NULL DEFAULT FALSE,
    recurring_rule_id   UUID,                                -- FK added after recurring_rules table
    receipt_id          UUID,                                -- FK added after receipts table
    ai_confidence       DECIMAL(5,4),                        -- 0.0000 – 1.0000  (AI categorization confidence)
    notes               TEXT,
    is_split            BOOLEAN         NOT NULL DEFAULT FALSE,
    is_deleted          BOOLEAN         NOT NULL DEFAULT FALSE,  -- soft delete
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_expenses_user         ON expenses (user_id);
CREATE INDEX idx_expenses_category     ON expenses (category_id);
CREATE INDEX idx_expenses_date         ON expenses (user_id, expense_date);
CREATE INDEX idx_expenses_source       ON expenses (source);
CREATE INDEX idx_expenses_vendor       ON expenses (vendor_name);
CREATE INDEX idx_expenses_tags         ON expenses USING GIN (tags);  -- full-text search on tags

-- 3.4  Expense Attachments (images, PDFs, etc.)
CREATE TABLE expense_attachments (
    attachment_id       UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    expense_id          UUID            NOT NULL REFERENCES expenses (expense_id) ON DELETE CASCADE,
    file_url            TEXT            NOT NULL,
    file_type           VARCHAR(50)     NOT NULL,            -- 'image/jpeg', 'application/pdf'
    file_size_bytes     BIGINT,
    original_filename   VARCHAR(255),
    uploaded_at         TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);


-- ############################################################################
-- MODULE 4 — RECEIPT & OCR PROCESSING
-- ############################################################################

-- 4.1  Receipts
CREATE TABLE receipts (
    receipt_id          UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID            NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    image_url           TEXT            NOT NULL,
    thumbnail_url       TEXT,
    ocr_status          VARCHAR(30)     NOT NULL DEFAULT 'pending',
                                                             -- 'pending','processing','completed','failed'
    raw_ocr_text        TEXT,                                -- full extracted text
    structured_data     JSONB,                               -- parsed JSON of receipt
    vendor_name         VARCHAR(255),
    receipt_date        DATE,
    subtotal            DECIMAL(15,2),
    tax_amount          DECIMAL(15,2),
    total_amount        DECIMAL(15,2),
    currency            VARCHAR(10)     DEFAULT 'INR',
    gst_number          VARCHAR(20),
    processing_time_ms  INT,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_receipts_user   ON receipts (user_id);
CREATE INDEX idx_receipts_status ON receipts (ocr_status);

-- 4.2  Receipt Line Items (individual items on a bill)
CREATE TABLE receipt_line_items (
    line_item_id        UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    receipt_id          UUID            NOT NULL REFERENCES receipts (receipt_id) ON DELETE CASCADE,
    item_name           VARCHAR(255)    NOT NULL,
    quantity            DECIMAL(10,3)   DEFAULT 1,
    unit_price          DECIMAL(15,2)   NOT NULL,
    total_price         DECIMAL(15,2)   NOT NULL,
    tax_rate            DECIMAL(5,2),                        -- e.g. 18.00 for 18% GST
    category_id         INT             REFERENCES categories (category_id) ON DELETE SET NULL,
    bounding_box        JSONB,                               -- OCR bounding box {x, y, w, h} for smart UI
    sort_order          INT             NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_line_items_receipt ON receipt_line_items (receipt_id);

-- Add foreign key from expenses → receipts
ALTER TABLE expenses
    ADD CONSTRAINT fk_expenses_receipt
    FOREIGN KEY (receipt_id) REFERENCES receipts (receipt_id) ON DELETE SET NULL;


-- ############################################################################
-- MODULE 5 — BILL SPLITTING
-- ############################################################################

-- 5.1  Split Groups (friends / housemates / trip groups)
CREATE TABLE split_groups (
    group_id            UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_by          UUID            NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    group_name          VARCHAR(150)    NOT NULL,
    group_icon          VARCHAR(50),
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- 5.2  Split Group Members (both registered users and external contacts)
CREATE TABLE split_group_members (
    member_id           UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    group_id            UUID            NOT NULL REFERENCES split_groups (group_id) ON DELETE CASCADE,
    user_id             UUID            REFERENCES users (user_id) ON DELETE SET NULL,   -- NULL if external
    external_name       VARCHAR(150),                        -- for non-registered contacts
    external_phone      VARCHAR(20),
    external_email      VARCHAR(255),
    joined_at           TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sgm_group ON split_group_members (group_id);
CREATE INDEX idx_sgm_user  ON split_group_members (user_id);

-- 5.3  Split Sessions (one bill-split event)
CREATE TABLE split_sessions (
    split_session_id    UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    expense_id          UUID            REFERENCES expenses (expense_id) ON DELETE SET NULL,
    receipt_id          UUID            REFERENCES receipts (receipt_id) ON DELETE SET NULL,
    group_id            UUID            REFERENCES split_groups (group_id) ON DELETE SET NULL,
    created_by          UUID            NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    split_method        VARCHAR(30)     NOT NULL DEFAULT 'equal',
                                                             -- 'equal','by_item','by_percentage','custom'
    total_amount        DECIMAL(15,2)   NOT NULL,
    currency            VARCHAR(10)     NOT NULL DEFAULT 'INR',
    notes               TEXT,
    is_settled          BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- 5.4  Split Shares (per-person share in a split)
CREATE TABLE split_shares (
    share_id            UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    split_session_id    UUID            NOT NULL REFERENCES split_sessions (split_session_id) ON DELETE CASCADE,
    member_id           UUID            NOT NULL REFERENCES split_group_members (member_id) ON DELETE CASCADE,
    share_amount        DECIMAL(15,2)   NOT NULL,
    is_paid             BOOLEAN         NOT NULL DEFAULT FALSE,
    paid_at             TIMESTAMPTZ,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_split_shares_session ON split_shares (split_session_id);

-- 5.5  Split Item Assignments (item-level mapping to members)
CREATE TABLE split_item_assignments (
    assignment_id       UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    split_session_id    UUID            NOT NULL REFERENCES split_sessions (split_session_id) ON DELETE CASCADE,
    line_item_id        UUID            NOT NULL REFERENCES receipt_line_items (line_item_id) ON DELETE CASCADE,
    member_id           UUID            NOT NULL REFERENCES split_group_members (member_id) ON DELETE CASCADE,
    share_fraction      DECIMAL(5,4)    NOT NULL DEFAULT 1.0000,  -- fraction of item assigned to this member
    amount              DECIMAL(15,2)   NOT NULL,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sia_session ON split_item_assignments (split_session_id);

-- 5.6  Settlement Ledger (tracks who owes whom)
CREATE TABLE settlements (
    settlement_id       UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    split_session_id    UUID            NOT NULL REFERENCES split_sessions (split_session_id) ON DELETE CASCADE,
    payer_member_id     UUID            NOT NULL REFERENCES split_group_members (member_id),
    payee_member_id     UUID            NOT NULL REFERENCES split_group_members (member_id),
    amount              DECIMAL(15,2)   NOT NULL,
    currency            VARCHAR(10)     NOT NULL DEFAULT 'INR',
    is_settled          BOOLEAN         NOT NULL DEFAULT FALSE,
    settled_at          TIMESTAMPTZ,
    settlement_method   VARCHAR(50),                         -- 'upi','cash','bank_transfer'
    settlement_reference TEXT,                               -- transaction ID
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);


-- ############################################################################
-- MODULE 6 — BUDGETS & FINANCIAL GOALS
-- ############################################################################

-- 6.1  Budgets
CREATE TABLE budgets (
    budget_id           UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID            NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    category_id         INT             REFERENCES categories (category_id) ON DELETE SET NULL,  -- NULL = total budget
    budget_type         VARCHAR(20)     NOT NULL DEFAULT 'monthly',
                                                             -- 'daily','weekly','monthly','yearly','custom'
    amount              DECIMAL(15,2)   NOT NULL CHECK (amount > 0),
    currency            VARCHAR(10)     NOT NULL DEFAULT 'INR',
    start_date          DATE            NOT NULL,
    end_date            DATE,
    rollover_enabled    BOOLEAN         NOT NULL DEFAULT FALSE,  -- carry over unused budget
    alert_threshold     DECIMAL(5,2)    NOT NULL DEFAULT 80.00,  -- % at which to alert
    is_active           BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_budgets_user     ON budgets (user_id);
CREATE INDEX idx_budgets_category ON budgets (user_id, category_id);

-- 6.2  Savings Goals
CREATE TABLE savings_goals (
    goal_id             UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID            NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    goal_name           VARCHAR(200)    NOT NULL,
    target_amount       DECIMAL(15,2)   NOT NULL CHECK (target_amount > 0),
    current_amount      DECIMAL(15,2)   NOT NULL DEFAULT 0,
    currency            VARCHAR(10)     NOT NULL DEFAULT 'INR',
    target_date         DATE,
    icon                VARCHAR(50),
    color               VARCHAR(7),
    is_completed        BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_savings_goals_user ON savings_goals (user_id);

-- 6.3  Savings Contributions
CREATE TABLE savings_contributions (
    contribution_id     UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    goal_id             UUID            NOT NULL REFERENCES savings_goals (goal_id) ON DELETE CASCADE,
    amount              DECIMAL(15,2)   NOT NULL,
    notes               TEXT,
    contributed_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);


-- ############################################################################
-- MODULE 7 — AUTOMATION ENGINE
-- ############################################################################

-- 7.1  Recurring Expense Rules
CREATE TABLE recurring_rules (
    rule_id             UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID            NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    category_id         INT             REFERENCES categories (category_id) ON DELETE SET NULL,
    payment_method_id   INT             REFERENCES payment_methods (payment_method_id) ON DELETE SET NULL,
    description         TEXT            NOT NULL,
    vendor_name         VARCHAR(255),
    amount              DECIMAL(15,2)   NOT NULL CHECK (amount > 0),
    currency            VARCHAR(10)     NOT NULL DEFAULT 'INR',
    frequency           VARCHAR(20)     NOT NULL,            -- 'daily','weekly','biweekly','monthly','quarterly','yearly'
    day_of_week         SMALLINT,                            -- 0=Mon … 6=Sun  (for weekly)
    day_of_month        SMALLINT,                            -- 1–31 (for monthly)
    month_of_year       SMALLINT,                            -- 1–12 (for yearly)
    start_date          DATE            NOT NULL,
    end_date            DATE,
    next_trigger_date   DATE            NOT NULL,
    last_triggered_at   TIMESTAMPTZ,
    is_active           BOOLEAN         NOT NULL DEFAULT TRUE,
    auto_approve        BOOLEAN         NOT NULL DEFAULT TRUE,   -- auto-create or require user confirmation
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_rr_user    ON recurring_rules (user_id);
CREATE INDEX idx_rr_trigger ON recurring_rules (next_trigger_date) WHERE is_active = TRUE;

-- Add foreign key from expenses → recurring_rules
ALTER TABLE expenses
    ADD CONSTRAINT fk_expenses_recurring_rule
    FOREIGN KEY (recurring_rule_id) REFERENCES recurring_rules (rule_id) ON DELETE SET NULL;

-- 7.2  Recurring Expense Execution Log
CREATE TABLE recurring_execution_log (
    execution_id        UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_id             UUID            NOT NULL REFERENCES recurring_rules (rule_id) ON DELETE CASCADE,
    expense_id          UUID            REFERENCES expenses (expense_id) ON DELETE SET NULL,
    status              VARCHAR(20)     NOT NULL,            -- 'success','failed','skipped','pending_approval'
    error_message       TEXT,
    executed_at         TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- 7.3  Bank & Email Integrations
CREATE TABLE bank_connections (
    connection_id       UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID            NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    institution_name    VARCHAR(255)    NOT NULL,
    account_type        VARCHAR(50),                         -- 'savings','current','credit_card'
    account_mask        VARCHAR(10),                         -- last 4 digits
    access_token_enc    BYTEA,                               -- encrypted access token
    refresh_token_enc   BYTEA,                               -- encrypted refresh token
    consent_id          VARCHAR(255),                        -- RBI Account Aggregator consent ID
    consent_expires_at  TIMESTAMPTZ,
    last_synced_at      TIMESTAMPTZ,
    sync_status         VARCHAR(30)     NOT NULL DEFAULT 'active',
                                                             -- 'active','expired','revoked','error'
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_bank_conn_user ON bank_connections (user_id);

-- 7.4  Email Integration (for parsing expense emails)
CREATE TABLE email_connections (
    connection_id       UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID            NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    email_address       VARCHAR(255)    NOT NULL,
    provider            VARCHAR(50)     NOT NULL,            -- 'gmail','outlook','yahoo'
    access_token_enc    BYTEA,
    refresh_token_enc   BYTEA,
    last_synced_at      TIMESTAMPTZ,
    is_active           BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- 7.5  Imported Transactions (staging before becoming expenses)
CREATE TABLE imported_transactions (
    transaction_id      UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID            NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    source              VARCHAR(50)     NOT NULL,            -- 'bank','email','sms'
    source_connection_id UUID,                               -- FK to bank_connections or email_connections
    raw_data            JSONB           NOT NULL,            -- original payload
    parsed_amount       DECIMAL(15,2),
    parsed_vendor       VARCHAR(255),
    parsed_date         DATE,
    parsed_category_id  INT             REFERENCES categories (category_id),
    ai_confidence       DECIMAL(5,4),
    status              VARCHAR(30)     NOT NULL DEFAULT 'pending',
                                                             -- 'pending','approved','rejected','auto_created'
    linked_expense_id   UUID            REFERENCES expenses (expense_id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    reviewed_at         TIMESTAMPTZ
);

CREATE INDEX idx_imported_tx_user   ON imported_transactions (user_id);
CREATE INDEX idx_imported_tx_status ON imported_transactions (status);


-- ############################################################################
-- MODULE 8 — CHATBOT & NATURAL LANGUAGE INTERACTION
-- ############################################################################

-- 8.1  Chat Sessions
CREATE TABLE chat_sessions (
    session_id          UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID            NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    title               VARCHAR(255),                        -- auto-generated title
    mode                VARCHAR(20)     NOT NULL DEFAULT 'text',
                                                             -- 'text','voice'
    started_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    ended_at            TIMESTAMPTZ,
    is_active           BOOLEAN         NOT NULL DEFAULT TRUE
);

CREATE INDEX idx_chat_sessions_user ON chat_sessions (user_id);

-- 8.2  Chat Messages
CREATE TABLE chat_messages (
    message_id          UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id          UUID            NOT NULL REFERENCES chat_sessions (session_id) ON DELETE CASCADE,
    role                VARCHAR(20)     NOT NULL,            -- 'user','assistant','system','tool'
    content             TEXT            NOT NULL,
    audio_url           TEXT,                                -- for voice messages
    intent              VARCHAR(100),                        -- 'add_expense','query_expense','get_summary','general'
    extracted_entities  JSONB,                               -- {amount, category, date, vendor, …}
    tool_calls          JSONB,                               -- function calls made by LLM
    linked_expense_id   UUID            REFERENCES expenses (expense_id) ON DELETE SET NULL,
    tokens_used         INT,
    latency_ms          INT,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_chat_messages_session ON chat_messages (session_id);

-- 8.3  Chatbot Feedback (thumbs up/down on responses)
CREATE TABLE chat_feedback (
    feedback_id         UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_id          UUID            NOT NULL REFERENCES chat_messages (message_id) ON DELETE CASCADE,
    user_id             UUID            NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    rating              SMALLINT        NOT NULL CHECK (rating IN (-1, 0, 1)),   -- -1=bad, 0=neutral, 1=good
    feedback_text       TEXT,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);


-- ############################################################################
-- MODULE 9 — AI RECOMMENDATIONS & INSIGHTS
-- ############################################################################

-- 9.1  AI Recommendations
CREATE TABLE ai_recommendations (
    recommendation_id   UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID            NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    recommendation_type VARCHAR(50)     NOT NULL,
                                                             -- 'budget_suggestion','savings_tip','investment_idea',
                                                             -- 'spending_alert','category_rebalance','subscription_review'
    title               VARCHAR(255)    NOT NULL,
    body                TEXT            NOT NULL,
    priority            VARCHAR(20)     NOT NULL DEFAULT 'medium',   -- 'low','medium','high','critical'
    related_category_id INT             REFERENCES categories (category_id),
    related_budget_id   UUID            REFERENCES budgets (budget_id) ON DELETE SET NULL,
    metadata            JSONB,                               -- additional context (savings potential, etc.)
    is_read             BOOLEAN         NOT NULL DEFAULT FALSE,
    is_dismissed        BOOLEAN         NOT NULL DEFAULT FALSE,
    is_actioned         BOOLEAN         NOT NULL DEFAULT FALSE,
    expires_at          TIMESTAMPTZ,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ai_rec_user ON ai_recommendations (user_id);
CREATE INDEX idx_ai_rec_type ON ai_recommendations (recommendation_type);

-- 9.2  Spending Anomalies (detected by ML)
CREATE TABLE spending_anomalies (
    anomaly_id          UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID            NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    expense_id          UUID            REFERENCES expenses (expense_id) ON DELETE SET NULL,
    anomaly_type        VARCHAR(50)     NOT NULL,            -- 'unusual_amount','new_vendor','category_spike','frequency_change'
    severity            VARCHAR(20)     NOT NULL DEFAULT 'info',   -- 'info','warning','critical'
    title               VARCHAR(255)    NOT NULL,
    description         TEXT,
    expected_value      DECIMAL(15,2),
    actual_value        DECIMAL(15,2),
    deviation_pct       DECIMAL(7,2),
    is_acknowledged     BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_anomalies_user ON spending_anomalies (user_id);

-- 9.3  Predictive Forecasts
CREATE TABLE spending_forecasts (
    forecast_id         UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID            NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    category_id         INT             REFERENCES categories (category_id),   -- NULL = overall
    forecast_period     VARCHAR(20)     NOT NULL,            -- 'weekly','monthly','quarterly'
    period_start        DATE            NOT NULL,
    period_end          DATE            NOT NULL,
    predicted_amount    DECIMAL(15,2)   NOT NULL,
    confidence_lower    DECIMAL(15,2),
    confidence_upper    DECIMAL(15,2),
    model_version       VARCHAR(50),
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_forecasts_user ON spending_forecasts (user_id);


-- ############################################################################
-- MODULE 10 — NOTIFICATIONS & ALERTS
-- ############################################################################

-- 10.1  Notification Templates
CREATE TABLE notification_templates (
    template_id         SERIAL          PRIMARY KEY,
    template_key        VARCHAR(100)    NOT NULL UNIQUE,     -- 'budget_80_pct','recurring_due','anomaly_detected'
    title_template      VARCHAR(255)    NOT NULL,            -- "Budget Alert: {{category}}"
    body_template       TEXT            NOT NULL,
    channels            TEXT[]          NOT NULL DEFAULT '{in_app}',  -- 'in_app','email','push','sms'
    is_active           BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- 10.2  User Notification Preferences
CREATE TABLE user_notification_preferences (
    pref_id             UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID            NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    template_id         INT             NOT NULL REFERENCES notification_templates (template_id) ON DELETE CASCADE,
    is_enabled          BOOLEAN         NOT NULL DEFAULT TRUE,
    channels            TEXT[],                              -- override per-template channels
    quiet_hours_start   TIME,
    quiet_hours_end     TIME,
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    UNIQUE (user_id, template_id)
);

-- 10.3  Notifications (actual sent/queued notifications)
CREATE TABLE notifications (
    notification_id     UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID            NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    template_id         INT             REFERENCES notification_templates (template_id),
    channel             VARCHAR(20)     NOT NULL,            -- 'in_app','email','push','sms'
    title               VARCHAR(255)    NOT NULL,
    body                TEXT            NOT NULL,
    action_url          TEXT,                                -- deep-link
    metadata            JSONB,
    is_read             BOOLEAN         NOT NULL DEFAULT FALSE,
    read_at             TIMESTAMPTZ,
    delivered_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_notifications_user   ON notifications (user_id);
CREATE INDEX idx_notifications_unread ON notifications (user_id) WHERE is_read = FALSE;


-- ############################################################################
-- MODULE 11 — DASHBOARD & ANALYTICS (MATERIALISED VIEWS / CACHE TABLES)
-- ############################################################################

-- 11.1  Daily Expense Aggregates (refreshed periodically)
CREATE TABLE daily_expense_summary (
    summary_id          UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID            NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    summary_date        DATE            NOT NULL,
    category_id         INT             REFERENCES categories (category_id),
    total_amount        DECIMAL(15,2)   NOT NULL DEFAULT 0,
    transaction_count   INT             NOT NULL DEFAULT 0,
    currency            VARCHAR(10)     NOT NULL DEFAULT 'INR',

    UNIQUE (user_id, summary_date, category_id)
);

CREATE INDEX idx_des_user_date ON daily_expense_summary (user_id, summary_date);

-- 11.2  Monthly Expense Aggregates
CREATE TABLE monthly_expense_summary (
    summary_id          UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID            NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    summary_year        SMALLINT        NOT NULL,
    summary_month       SMALLINT        NOT NULL,
    category_id         INT             REFERENCES categories (category_id),
    total_amount        DECIMAL(15,2)   NOT NULL DEFAULT 0,
    transaction_count   INT             NOT NULL DEFAULT 0,
    budget_amount       DECIMAL(15,2),
    budget_utilization  DECIMAL(5,2),                        -- percentage used
    currency            VARCHAR(10)     NOT NULL DEFAULT 'INR',

    UNIQUE (user_id, summary_year, summary_month, category_id)
);

CREATE INDEX idx_mes_user_period ON monthly_expense_summary (user_id, summary_year, summary_month);

-- 11.3  User Financial Snapshot (latest computed state)
CREATE TABLE user_financial_snapshot (
    snapshot_id         UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID            NOT NULL UNIQUE REFERENCES users (user_id) ON DELETE CASCADE,
    total_spent_mtd     DECIMAL(15,2)   NOT NULL DEFAULT 0,  -- month to date
    total_spent_ytd     DECIMAL(15,2)   NOT NULL DEFAULT 0,  -- year to date
    avg_daily_spend     DECIMAL(15,2)   NOT NULL DEFAULT 0,
    top_category_id     INT             REFERENCES categories (category_id),
    top_category_pct    DECIMAL(5,2),
    total_budget_mtd    DECIMAL(15,2),
    remaining_budget    DECIMAL(15,2),
    savings_rate        DECIMAL(5,2),                        -- % of income saved
    currency            VARCHAR(10)     NOT NULL DEFAULT 'INR',
    computed_at         TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);


-- ############################################################################
-- MODULE 12 — SMART SEARCH & FULL-TEXT INDEX
-- ############################################################################

-- 12.1  Search Index (optional — for PostgreSQL full-text search)
CREATE TABLE expense_search_index (
    expense_id          UUID            PRIMARY KEY REFERENCES expenses (expense_id) ON DELETE CASCADE,
    search_vector       TSVECTOR        NOT NULL
);

CREATE INDEX idx_search_vector ON expense_search_index USING GIN (search_vector);

-- Trigger to auto-populate search vector (PostgreSQL)
CREATE OR REPLACE FUNCTION fn_update_expense_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO expense_search_index (expense_id, search_vector)
    VALUES (
        NEW.expense_id,
        to_tsvector('english',
            COALESCE(NEW.description, '') || ' ' ||
            COALESCE(NEW.vendor_name, '') || ' ' ||
            COALESCE(NEW.notes, '') || ' ' ||
            COALESCE(array_to_string(NEW.tags, ' '), '')
        )
    )
    ON CONFLICT (expense_id) DO UPDATE
    SET search_vector = EXCLUDED.search_vector;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_expense_search_vector
    AFTER INSERT OR UPDATE ON expenses
    FOR EACH ROW
    EXECUTE FUNCTION fn_update_expense_search_vector();


-- ############################################################################
-- MODULE 13 — AUDIT TRAIL & SYSTEM LOGS
-- ############################################################################

-- 13.1  Audit Log (tracks all sensitive data changes)
CREATE TABLE audit_log (
    log_id              UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID            REFERENCES users (user_id) ON DELETE SET NULL,
    action              VARCHAR(50)     NOT NULL,            -- 'CREATE','UPDATE','DELETE','LOGIN','EXPORT'
    entity_type         VARCHAR(50)     NOT NULL,            -- 'expense','budget','settings',...
    entity_id           UUID,
    old_value           JSONB,
    new_value           JSONB,
    ip_address          INET,
    user_agent          TEXT,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_user     ON audit_log (user_id);
CREATE INDEX idx_audit_entity   ON audit_log (entity_type, entity_id);
CREATE INDEX idx_audit_created  ON audit_log (created_at);

-- 13.2  API Request Log (for performance monitoring)
CREATE TABLE api_request_log (
    request_id          UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID            REFERENCES users (user_id) ON DELETE SET NULL,
    method              VARCHAR(10)     NOT NULL,            -- 'GET','POST','PUT','DELETE'
    endpoint            VARCHAR(500)    NOT NULL,
    status_code         SMALLINT        NOT NULL,
    request_body        JSONB,
    response_time_ms    INT             NOT NULL,
    ip_address          INET,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_api_log_user     ON api_request_log (user_id);
CREATE INDEX idx_api_log_endpoint ON api_request_log (endpoint);

-- 13.3  LLM Usage Tracking (token consumption, costs)
CREATE TABLE llm_usage_log (
    usage_id            UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID            NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    model_name          VARCHAR(100)    NOT NULL,            -- 'gpt-4','claude-3','llama-3'
    feature             VARCHAR(100)    NOT NULL,            -- 'chatbot','categorization','recommendation','summary'
    prompt_tokens       INT             NOT NULL DEFAULT 0,
    completion_tokens   INT             NOT NULL DEFAULT 0,
    total_tokens        INT             NOT NULL DEFAULT 0,
    cost_usd            DECIMAL(10,6)   DEFAULT 0,
    latency_ms          INT,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_llm_usage_user ON llm_usage_log (user_id);


-- ############################################################################
-- MODULE 14 — CACHE / IN-MEMORY SUPPORT TABLES
-- ############################################################################

-- 14.1  API Cache (for FastAPI response caching layer)
CREATE TABLE cache_store (
    cache_key           VARCHAR(500)    PRIMARY KEY,
    cache_value         JSONB           NOT NULL,
    expires_at          TIMESTAMPTZ     NOT NULL,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_cache_expiry ON cache_store (expires_at);


-- ############################################################################
-- MODULE 15 — DATA EXPORT & REPORTING
-- ############################################################################

-- 15.1  Export Requests
CREATE TABLE export_requests (
    export_id           UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID            NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    export_type         VARCHAR(20)     NOT NULL,            -- 'csv','pdf','json','excel'
    date_range_start    DATE,
    date_range_end      DATE,
    filters             JSONB,                               -- {categories: [...], payment_methods: [...]}
    file_url            TEXT,
    status              VARCHAR(30)     NOT NULL DEFAULT 'pending',
                                                             -- 'pending','processing','completed','failed'
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    completed_at        TIMESTAMPTZ
);


-- ============================================================================
-- FINAL NOTES
-- ============================================================================
-- • All timestamps use TIMESTAMPTZ for timezone awareness.
-- • Soft deletes (is_deleted) used on core tables; hard deletes via cascade 
--   on child tables.
-- • UUIDs used for primary keys to support distributed systems / API exposure.
-- • JSONB columns used for flexible / semi-structured data (OCR results,
--   metadata, extracted entities).
-- • GIN indexes used for array & full-text search columns.
-- • Envelope encryption pattern: per-user DEK encrypted by a master KEK
--   stored in a KMS (AWS KMS / HashiCorp Vault).
-- • Summary / aggregate tables (Module 11) should be refreshed by a 
--   scheduled job (e.g., Celery beat, cron, pg_cron).
-- ============================================================================
