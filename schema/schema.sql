-- ============================================================================
-- Expense Manager — Simplified Schema (College Project)
-- Only 4 tables: users, categories, expenses, budgets
-- ============================================================================

-- Users
CREATE TABLE IF NOT EXISTS users (
    user_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       VARCHAR(255) UNIQUE NOT NULL,
    full_name   VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL DEFAULT 'demo',
    preferred_currency VARCHAR(3) DEFAULT 'INR',
    avatar      TEXT,
    dark_mode   BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Categories (system defaults + user-defined)
CREATE TABLE IF NOT EXISTS categories (
    category_id SERIAL PRIMARY KEY,
    name        VARCHAR(50) NOT NULL,
    icon        VARCHAR(10) DEFAULT '📌',
    color       VARCHAR(7) DEFAULT '#D5DBDB',
    is_default  BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Expenses
CREATE TABLE IF NOT EXISTS expenses (
    expense_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(user_id),
    amount      NUMERIC(12,2) NOT NULL,
    category_id INTEGER REFERENCES categories(category_id),
    expense_date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_expenses_user ON expenses(user_id);
CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(expense_date);
CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category_id);

-- Budgets
CREATE TABLE IF NOT EXISTS budgets (
    budget_id   SERIAL PRIMARY KEY,
    user_id     UUID NOT NULL REFERENCES users(user_id),
    category_id INTEGER REFERENCES categories(category_id),
    amount      NUMERIC(12,2) NOT NULL,
    month       VARCHAR(7) NOT NULL,  -- e.g. '2026-02'
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, category_id, month)
);

-- Seed default categories
INSERT INTO categories (name, icon, color) VALUES
    ('Food',           '🍔', '#FF6B6B'),
    ('Transport',      '🚗', '#45B7D1'),
    ('Shopping',       '🛍️', '#96CEB4'),
    ('Bills',          '💡', '#DDA0DD'),
    ('Entertainment',  '🎬', '#FFEAA7'),
    ('Others',         '📌', '#D5DBDB')
ON CONFLICT DO NOTHING;
