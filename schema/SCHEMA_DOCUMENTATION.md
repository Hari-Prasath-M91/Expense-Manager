# Expense Manager — Database Schema

## Overview
A high-performance PostgreSQL schema designed for AI-driven financial insights and automated transaction tracking from external sources (like Gmail).

## Tables

### 👤 `users`
| Column | Type | Description |
|--------|------|-------------|
| user_id | UUID | Primary key |
| google_id | VARCHAR(255) | Unique identifier for Google OAuth sessions |
| email | VARCHAR(255) | Unique user email |
| preferred_currency | VARCHAR(3)| Default 'INR'. Used for auto-conversion |
| google_refresh_token | TEXT | Persistent token for long-term Gmail syncing |
| dark_mode | BOOLEAN | User interface preference |

### 🗂️ `categories`
| Column | Type | Description |
|--------|------|-------------|
| category_id | SERIAL | Primary key |
| name | VARCHAR(50) | Unique name (e.g., Food, Travel) |
| icon | VARCHAR(10) | Emoji representation |
| is_default | BOOLEAN | System-provided vs User-defined |

### 🧾 `expenses`
| Column | Type | Description |
|--------|------|-------------|
| expense_id | UUID | Primary key |
| user_id | UUID | Foreign Key → `users` |
| amount | NUMERIC(12,2) | Value (stored with 2 decimal precision) |
| category_id | INTEGER | Foreign Key → `categories` |
| expense_date | DATE | Actual date of transaction |
| gmail_msg_id | VARCHAR(255) | Link to source email (prevents duplicates) |

### 📅 `budgets`
| Column | Type | Description |
|--------|------|-------------|
| budget_id | SERIAL | Primary key |
| user_id | UUID | Foreign Key → `users` |
| category_id | INTEGER | Linked spending category |
| amount | NUMERIC(12,2) | Monthly limit |
| month | VARCHAR(7) | Format: 'YYYY-MM' |

### 📩 `gmail_scanned_ids`
| Column | Type | Description |
|--------|------|-------------|
| scan_id | SERIAL | Primary key |
| user_id | UUID | Foreign Key → `users` |
| msg_id | VARCHAR(255) | Gmail message ID that was processed |
| scanned_at| TIMESTAMPTZ | timestamp of the scan |