# 🗄️ AI-Powered Personal Expense Manager — Database Schema Documentation

> **Version**: 1.0  
> **Database**: PostgreSQL (recommended) / SQLite (development fallback)  
> **Last Updated**: 2026-02-23  

---

## 📋 Table of Contents

1. [Schema Overview](#schema-overview)
2. [Module 1 — Authentication & User Management](#module-1--authentication--user-management)
3. [Module 2 — Privacy, Consent & Access Control](#module-2--privacy-consent--access-control)
4. [Module 3 — Expense Storage Engine](#module-3--expense-storage-engine)
5. [Module 4 — Receipt & OCR Processing](#module-4--receipt--ocr-processing)
6. [Module 5 — Bill Splitting](#module-5--bill-splitting)
7. [Module 6 — Budgets & Financial Goals](#module-6--budgets--financial-goals)
8. [Module 7 — Automation Engine](#module-7--automation-engine)
9. [Module 8 — Chatbot & NLP Interaction](#module-8--chatbot--nlp-interaction)
10. [Module 9 — AI Recommendations & Insights](#module-9--ai-recommendations--insights)
11. [Module 10 — Notifications & Alerts](#module-10--notifications--alerts)
12. [Module 11 — Dashboard & Analytics](#module-11--dashboard--analytics)
13. [Module 12 — Smart Search](#module-12--smart-search)
14. [Module 13 — Audit Trail & System Logs](#module-13--audit-trail--system-logs)
15. [Module 14 — Cache Support](#module-14--cache-support)
16. [Module 15 — Data Export & Reporting](#module-15--data-export--reporting)
17. [Entity Relationship Diagram](#entity-relationship-diagram)
18. [Design Decisions](#design-decisions)

---

## Schema Overview

| # | Module | Tables | Purpose |
|---|--------|--------|---------|
| 1 | Authentication | `users`, `oauth_providers`, `sessions`, `password_reset_tokens`, `email_verification_tokens` | User identity, login, session management |
| 2 | Privacy & Access | `roles`, `user_roles`, `user_privacy_settings`, `consent_audit_log`, `user_encryption_keys` | RBAC, GDPR compliance, encryption |
| 3 | Expense Storage | `categories`, `payment_methods`, `expenses`, `expense_attachments` | Core expense CRUD |
| 4 | Receipt & OCR | `receipts`, `receipt_line_items` | Bill scanning, OCR parsing |
| 5 | Bill Splitting | `split_groups`, `split_group_members`, `split_sessions`, `split_shares`, `split_item_assignments`, `settlements` | Group expense splitting |
| 6 | Budgets & Goals | `budgets`, `savings_goals`, `savings_contributions` | Financial planning |
| 7 | Automation | `recurring_rules`, `recurring_execution_log`, `bank_connections`, `email_connections`, `imported_transactions` | Auto-logging, bank/email sync |
| 8 | Chatbot | `chat_sessions`, `chat_messages`, `chat_feedback` | NLP interaction, voice |
| 9 | AI Insights | `ai_recommendations`, `spending_anomalies`, `spending_forecasts` | ML-driven insights |
| 10 | Notifications | `notification_templates`, `user_notification_preferences`, `notifications` | Alerts & reminders |
| 11 | Dashboard | `daily_expense_summary`, `monthly_expense_summary`, `user_financial_snapshot` | Pre-computed analytics |
| 12 | Search | `expense_search_index` | Full-text search |
| 13 | Audit | `audit_log`, `api_request_log`, `llm_usage_log` | Compliance, monitoring |
| 14 | Cache | `cache_store` | API response caching |
| 15 | Export | `export_requests` | Data export jobs |

**Total: 42 tables across 15 modules**

---

## Module 1 — Authentication & User Management

### `users`
Central user table. Every other table references this.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `user_id` | UUID | PK, auto | Unique user identifier |
| `email` | VARCHAR(255) | UNIQUE, NOT NULL | Login email |
| `password_hash` | VARCHAR(512) | NOT NULL | bcrypt/argon2 hash |
| `full_name` | VARCHAR(150) | NOT NULL | Display name |
| `phone_number` | VARCHAR(20) | | Mobile number |
| `profile_picture_url` | TEXT | | Avatar URL |
| `preferred_currency` | VARCHAR(10) | DEFAULT 'INR' | User's currency |
| `locale` | VARCHAR(10) | DEFAULT 'en-IN' | Language/locale |
| `timezone` | VARCHAR(50) | DEFAULT 'Asia/Kolkata' | Timezone |
| `is_active` | BOOLEAN | DEFAULT TRUE | Account status |
| `is_verified` | BOOLEAN | DEFAULT FALSE | Email verified? |
| `created_at` | TIMESTAMPTZ | auto | Registration time |
| `updated_at` | TIMESTAMPTZ | auto | Last update |

### `oauth_providers`
Stores OAuth credentials for social login (Google, GitHub, etc.).

### `sessions`
Tracks active login sessions with device info and IP for security.

### `password_reset_tokens` / `email_verification_tokens`
Time-limited tokens for password recovery and email verification flows.

---

## Module 2 — Privacy, Consent & Access Control

### `roles` + `user_roles`
Role-Based Access Control (RBAC). Default roles: `user`, `premium`, `admin`.

### `user_privacy_settings`
Per-user privacy preferences:
- **allow_analytics** — opt in/out of usage analytics
- **allow_ai_training** — consent for AI model training on their data
- **data_retention_days** — how long to retain expense data

### `consent_audit_log`
GDPR-compliant audit trail of all consent grants/revocations.

### `user_encryption_keys`
Envelope encryption — each user gets a Data Encryption Key (DEK) encrypted by a master Key Encryption Key (KEK) from a KMS.

---

## Module 3 — Expense Storage Engine

### `categories`
Hierarchical expense categories (supports parent-child via `parent_category_id`).
- **System defaults**: Food, Groceries, Transport, Shopping, etc. (15 pre-seeded)
- **User custom**: Users can create their own categories

### `payment_methods`
User payment instruments: cash, UPI, credit/debit cards, wallets, net banking.

### `expenses` ⭐ (Core Table)
The central fact table for all expenses.

| Key Column | Description |
|------------|-------------|
| `source` | How the expense was created: `manual`, `chatbot`, `nlp`, `ocr`, `bank_import`, `email`, `recurring`, `voice` |
| `ai_confidence` | Confidence score (0–1) when AI auto-categorized |
| `is_recurring` | Flag for recurring expenses |
| `is_split` | Flag for split bills |
| `tags` | Array column for user-defined tags (GIN indexed) |
| `latitude` / `longitude` | Location tracking |

### `expense_attachments`
Multiple file attachments per expense (receipt photos, PDFs).

---

## Module 4 — Receipt & OCR Processing

### `receipts`
Tracks uploaded receipt images and their OCR processing status.

| Key Column | Description |
|------------|-------------|
| `ocr_status` | Processing pipeline: `pending` → `processing` → `completed` / `failed` |
| `raw_ocr_text` | Full extracted text for search |
| `structured_data` | JSONB parsed receipt data |
| `gst_number` | For Indian GST receipts |

### `receipt_line_items`
Individual items on a bill:
- `bounding_box` (JSONB) — OCR coordinates for **Smart UI tap-to-assign** during bill splitting
- `tax_rate` — Per-item tax for accurate splitting

---

## Module 5 — Bill Splitting

### Flow
```
split_groups → split_group_members
                     ↓
              split_sessions → split_shares (per-person totals)
                     ↓
        split_item_assignments (item-level mapping)
                     ↓
              settlements (who owes whom)
```

### `split_groups`
Named groups (e.g., "Flatmates", "Weekend Trip").

### `split_group_members`
Supports both registered users (`user_id`) and external contacts (`external_name`, `external_phone`).

### `split_sessions`
One split event. Supports methods:
- **equal** — divide total equally
- **by_item** — assign individual line items to people
- **by_percentage** — custom percentage splits
- **custom** — manual amount assignment

### `split_item_assignments`
Maps receipt line items to group members with a `share_fraction` for partial item sharing.

### `settlements`
Ledger tracking debts and payments between members.

---

## Module 6 — Budgets & Financial Goals

### `budgets`
Category-level or overall budgets with:
- Multiple periods: daily, weekly, monthly, yearly, custom
- **Rollover** support — unused budget carries forward
- **Alert threshold** — notify at X% usage (default: 80%)

### `savings_goals`
Named financial targets (e.g., "Emergency Fund ₹1,00,000").

### `savings_contributions`
Individual contributions towards savings goals.

---

## Module 7 — Automation Engine

### `recurring_rules`
Defines automated expense creation rules:
- Flexible frequencies: daily, weekly, biweekly, monthly, quarterly, yearly
- `auto_approve` flag — create automatically or require user confirmation
- `next_trigger_date` — pre-computed for efficient scheduling

### `recurring_execution_log`
Tracks every execution of a recurring rule with status and error messages.

### `bank_connections`
Stores encrypted bank integration credentials:
- Supports RBI Account Aggregator consent framework
- Tracks sync status and last sync time

### `email_connections`
Email integration for parsing expense emails (Gmail, Outlook, Yahoo).

### `imported_transactions`
**Staging table** — imported bank/email transactions land here first:
1. AI parses and categorizes (`ai_confidence` score)
2. User reviews and approves/rejects
3. Approved transactions become `expenses`

---

## Module 8 — Chatbot & NLP Interaction

### `chat_sessions`
Conversation containers. Supports `text` and `voice` modes.

### `chat_messages`
Individual messages with:
- `intent` — Classified intent: `add_expense`, `query_expense`, `get_summary`, `general`
- `extracted_entities` — JSONB with parsed amount, category, date, vendor
- `tool_calls` — LLM function calls for expense operations
- `audio_url` — Voice message recordings
- `linked_expense_id` — Links to expenses created via chatbot

### Use Cases Supported
| User Input | Intent | Action |
|-----------|--------|--------|
| "Add ₹250 for cab ride yesterday" | `add_expense` | Extract entities → create expense |
| "How much did I spend on food last month?" | `query_expense` | Query expenses → return summary |
| "Give me a summary of last month" | `get_summary` | Aggregate and format report |

### `chat_feedback`
Thumbs up/down on AI responses for quality improvement.

---

## Module 9 — AI Recommendations & Insights

### `ai_recommendations`
Personalized financial advice:
- **Types**: `budget_suggestion`, `savings_tip`, `investment_idea`, `spending_alert`, `category_rebalance`, `subscription_review`
- **Priority levels**: low, medium, high, critical
- **Lifecycle**: created → read → actioned / dismissed

### `spending_anomalies`
ML-detected unusual patterns:
- `unusual_amount` — significantly higher than normal
- `new_vendor` — first-time merchant
- `category_spike` — sudden increase in a category
- `frequency_change` — spending frequency deviation

### `spending_forecasts`
Predictive spending estimates with confidence intervals.

---

## Module 10 — Notifications & Alerts

### Template-based system:
1. `notification_templates` — Define notification types (budget alerts, recurring dues, anomalies)
2. `user_notification_preferences` — Per-user channel preferences with quiet hours
3. `notifications` — Actual sent notifications with read tracking

### Supported Channels
- `in_app` — In-application notifications
- `email` — Email alerts
- `push` — Mobile push notifications
- `sms` — SMS messages

---

## Module 11 — Dashboard & Analytics

Pre-computed aggregate tables for fast dashboard rendering:

### `daily_expense_summary`
Per-user, per-category daily totals. Powers daily trend charts.

### `monthly_expense_summary`
Monthly aggregates with budget utilization percentages. Powers:
- Pie charts (category breakdown)
- Bar graphs (monthly comparison)
- Budget vs. actual reports

### `user_financial_snapshot`
Latest computed financial state:
- Month-to-date / Year-to-date spending
- Average daily spend
- Top spending category
- Remaining budget
- Savings rate

> **Note**: These tables are refreshed by a scheduled background job (Celery beat / pg_cron).

---

## Module 12 — Smart Search

### `expense_search_index`
PostgreSQL full-text search using `tsvector`:
- Indexes: description, vendor name, notes, tags
- Supports queries like:
  - "McDonald's bills"
  - "GST 18%"
  - "Above ₹1000 in October"

Auto-populated via trigger on the `expenses` table.

---

## Module 13 — Audit Trail & System Logs

### `audit_log`
Tracks all sensitive data changes with before/after values (JSONB).

### `api_request_log`
API performance monitoring — endpoint, response time, status code.

### `llm_usage_log`
Token consumption and cost tracking per LLM call:
- Feature-level tracking: chatbot, categorization, recommendation, summary
- Supports multiple models: GPT-4, Claude, Llama, etc.

---

## Module 14 — Cache Support

### `cache_store`
Database-backed cache for FastAPI response caching:
- Key-value store with TTL (expiration)
- Complement to in-memory caching (Redis)

---

## Module 15 — Data Export & Reporting

### `export_requests`
Async export job tracking:
- Formats: CSV, PDF, JSON, Excel
- Supports date range and category filters
- Status pipeline: `pending` → `processing` → `completed` / `failed`

---

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CORE RELATIONSHIPS                          │
└─────────────────────────────────────────────────────────────────────┘

                              ┌──────────┐
                              │  users   │
                              └────┬─────┘
                 ┌────────────┬────┼────┬────────────┬──────────────┐
                 │            │    │    │            │              │
                 ▼            ▼    │    ▼            ▼              ▼
          ┌──────────┐  ┌─────────┐│ ┌──────────┐ ┌──────────┐ ┌─────────────┐
          │  oauth   │  │sessions ││ │ budgets  │ │ savings  │ │  privacy    │
          │providers │  │         ││ │          │ │ _goals   │ │  settings   │
          └──────────┘  └─────────┘│ └──────────┘ └─────┬────┘ └─────────────┘
                                   │                    │
                 ┌────────────┬────┼────┬───────────────┤
                 │            │    │    │               │
                 ▼            ▼    │    ▼               ▼
          ┌──────────┐  ┌─────────┐│ ┌──────────┐ ┌───────────────┐
          │categories│  │payment  ││ │recurring │ │   savings     │
          │          │  │_methods ││ │ _rules   │ │contributions  │
          └────┬─────┘  └────┬────┘│ └────┬─────┘ └───────────────┘
               │             │     │      │
               └──────┬──────┘     │      │
                      │            │      │
                      ▼            │      │
               ┌──────────────┐    │      │
               │   expenses   │◄───┘      │
               │   (CORE)     │◄──────────┘
               └──────┬───────┘
          ┌───────┬───┼───┬──────────┐
          │       │   │   │          │
          ▼       ▼   │   ▼          ▼
   ┌──────────┐ ┌───┐│┌──────┐ ┌──────────┐
   │attachmnts│ │OCR│││search│ │  split   │
   └──────────┘ │   │││index │ │ sessions │
                ▼   │ └──────┘ └────┬─────┘
          ┌─────────┐│              │
          │receipts ││         ┌────┼────────┐
          └────┬────┘│         │    │        │
               │     │         ▼    ▼        ▼
               ▼     │    ┌──────┐┌─────┐┌──────────┐
         ┌─────────┐ │    │shares││items││settlements│
         │  line   │ │    └──────┘│assn │└──────────┘
         │  items  │ │            └─────┘
         └─────────┘ │
                     │
    ┌────────────────┼────────────────────────────┐
    │                │                            │
    ▼                ▼                            ▼
┌─────────┐   ┌───────────┐              ┌──────────────┐
│ chatbot │   │ AI reco-  │              │ notifications│
│sessions │   │mmendations│              │              │
└────┬────┘   └───────────┘              └──────────────┘
     │
     ▼
┌──────────┐
│ messages │
└──────────┘
```

---

## Design Decisions

### 1. **UUID Primary Keys**
All primary keys are UUIDs (v4) instead of auto-incrementing integers:
- Safe for API exposure (no enumeration attacks)
- Supports distributed systems and horizontal scaling
- Compatible with offline-first mobile apps

### 2. **Soft Deletes on Core Tables**
The `expenses` table uses `is_deleted` for soft deletes:
- Preserves data for audit trails and undo functionality
- Child tables use `ON DELETE CASCADE` for hard deletes when parent is hard-deleted

### 3. **JSONB for Semi-Structured Data**
Used JSONB columns for:
- OCR structured data (varies by receipt format)
- Chat extracted entities (varies by intent)
- Notification metadata
- Import raw data

### 4. **Envelope Encryption**
Per-user Data Encryption Keys (DEKs) stored encrypted by a master Key Encryption Key (KEK):
- KEK stored in cloud KMS (AWS KMS / HashiCorp Vault)
- DEK rotation supported via `key_version`
- Minimizes blast radius if a single key is compromised

### 5. **Staging Table Pattern for Imports**
`imported_transactions` acts as a staging area:
- Raw data preserved before transformation
- User approval required before creating actual expenses
- AI confidence scores guide auto-approval thresholds

### 6. **Pre-Computed Aggregates**
Dashboard summary tables (`daily_expense_summary`, `monthly_expense_summary`, `user_financial_snapshot`):
- Avoids expensive real-time aggregation queries
- Refreshed by scheduled background jobs
- Trades slight data staleness for significant performance gain

### 7. **Full-Text Search**
PostgreSQL native `tsvector` for expense search:
- Supports natural language queries
- GIN index for fast lookups
- Auto-maintained via trigger

### 8. **Template-Based Notifications**
Notification templates with per-user preference overrides:
- Easy to add new notification types
- Users control channels and quiet hours
- Supports multi-channel delivery

### 9. **LLM Usage Tracking**
Dedicated table for AI/LLM cost monitoring:
- Per-feature token tracking
- Multi-model support
- Enables cost optimization and usage quotas

### 10. **GIN Indexes on Arrays**
Tags array on `expenses` indexed with GIN:
- Fast tag-based filtering
- Supports "contains" and "overlaps" queries

---

## Index Summary

| Table | Index | Type | Purpose |
|-------|-------|------|---------|
| `users` | `idx_users_email` | B-tree | Email lookup |
| `expenses` | `idx_expenses_user` | B-tree | User's expenses |
| `expenses` | `idx_expenses_date` | B-tree | Date range queries |
| `expenses` | `idx_expenses_tags` | GIN | Tag-based filtering |
| `expense_search_index` | `idx_search_vector` | GIN | Full-text search |
| `notifications` | `idx_notifications_unread` | Partial | Unread notifications |
| `recurring_rules` | `idx_rr_trigger` | Partial | Active rules by trigger date |
| `audit_log` | `idx_audit_created` | B-tree | Time-based audit queries |

---

## Quick Start

```sql
-- 1. Create the database
CREATE DATABASE expense_manager;

-- 2. Connect and run the schema
\c expense_manager
\i schema.sql

-- 3. Create your first user (in application code, not raw SQL)
-- Password should be hashed with bcrypt/argon2 before storage
```

---

*Schema designed for the AI-Powered Personal Expense Manager project.*
