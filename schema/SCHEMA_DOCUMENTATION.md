# Expense Manager — Database Schema

## Overview
A minimalist PostgreSQL schema with 4 core tables for high-performance financial tracking and AI-driven insights.

## Core Tables

### 👤 `users`
| Column | Type | Description |
|--------|------|-------------|
| user_id | UUID | Primary key, default `gen_random_uuid()` |
| email | VARCHAR(255) | Unique identifier |
| full_name | VARCHAR(100) | User's display name |
| password_hash | VARCHAR(255)| Default 'demo' |
| preferred_currency | VARCHAR(3)| Default 'INR' |
| avatar | TEXT | URL to user's profile picture |
| dark_mode | BOOLEAN | User interface preference |
| created_at | TIMESTAMPTZ | Automatic timestamp |

### 🗂️ `categories`
| Column | Type | Description |
|--------|------|-------------|
| category_id | SERIAL | Primary key |
| name | VARCHAR(50) | Friendly name (e.g., Food, Travel) |
| icon | VARCHAR(10) | Emoji representation |
| color | VARCHAR(7) | Hex code for UI representation |
| is_default | BOOLEAN | System-provided categories |
| created_at | TIMESTAMPTZ | Automatic timestamp |

### 🧾 `expenses`
| Column | Type | Description |
|--------|------|-------------|
| expense_id | UUID | Primary key |
| user_id | UUID | Foreign Key → `users` |
| amount | NUMERIC(12,2) | Transaction value |
| category_id | INTEGER | Foreign Key → `categories` |
| expense_date | DATE | Actual date of transaction |
| created_at | TIMESTAMPTZ | Creation timestamp |

### 📅 `budgets`
| Column | Type | Description |
|--------|------|-------------|
| budget_id | SERIAL | Primary key |
| user_id | UUID | Foreign Key → `users` |
| category_id | INTEGER | Foreign Key → `categories` |
| amount | NUMERIC(12,2) | Monthly limit |
| month | VARCHAR(7) | Format: 'YYYY-MM' |
| created_at | TIMESTAMPTZ | Creation timestamp |

## Relationships
- One **User** has Many **Expenses** (1:N)
- One **User** has Many **Budgets** (1:N)
- One **Category** is linked to Many **Expenses** (1:N)
- One **Category** is linked to Many **Budgets** (1:N)

## Default Seed Categories
Seeded with **Food**, **Transport**, **Shopping**, **Bills**, **Entertainment**, and **Others** with curated colors.
