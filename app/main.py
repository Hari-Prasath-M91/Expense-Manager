# ============================================================================
# FastAPI Application — PostgreSQL REST Endpoint for HF Spaces
# ============================================================================
"""
Provides HTTP REST endpoints to interact with the Expense Manager PostgreSQL
database.  Designed to run inside a Hugging Face Spaces Docker container.
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import asyncpg
from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.config import settings
from app.database import DatabasePool


# ---------------------------------------------------------------------------
# Lifespan — manage DB pool
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(application: FastAPI):
    """Create DB connection pool on startup, close on shutdown."""
    application.state.db = DatabasePool()
    await application.state.db.connect()
    yield
    await application.state.db.disconnect()


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="💰 Expense Manager — Database API",
    description=(
        "REST API for the AI-Powered Personal Expense Manager database. "
        "Deployed on Hugging Face Spaces with PostgreSQL backend."
    ),
    version="1.0.0",
    docs_url="/",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS — allow all origins (adjust in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===========================================================================
# Helper
# ===========================================================================
def _get_db(request: Request) -> DatabasePool:
    return request.app.state.db


# ===========================================================================
# Health & Info
# ===========================================================================
@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint for Docker / HF Spaces."""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/info", tags=["System"])
async def system_info(request: Request):
    """System information and database connection status."""
    db: DatabasePool = _get_db(request)
    db_status = "unknown"
    table_count = 0

    try:
        table_count = await db.fetchval(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"
        )
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {e}"

    return {
        "service": "Expense Manager Database API",
        "version": "1.0.0",
        "database": db_status,
        "tables": table_count,
        "docs": "/",
    }


@app.post("/schema/initialize", tags=["System"])
async def initialize_schema(request: Request):
    """
    Apply the database schema from schema.sql to the connected database.
    
    Idempotent — uses IF NOT EXISTS / ON CONFLICT where applicable.
    Call this once after first deployment on Render to set up all tables.
    """
    import pathlib

    db = _get_db(request)

    # Check if schema is already applied
    table_count = await db.fetchval(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"
    )
    if table_count and table_count >= 30:
        return {
            "status": "skipped",
            "message": f"Schema already exists ({table_count} tables found). No action taken.",
            "tables": table_count,
        }

    # Read and execute schema.sql
    schema_path = pathlib.Path(__file__).parent.parent / "schema" / "schema.sql"
    if not schema_path.exists():
        raise HTTPException(status_code=500, detail="schema.sql not found in container")

    schema_sql = schema_path.read_text(encoding="utf-8")

    try:
        async with db._pool.acquire() as conn:
            await conn.execute(schema_sql)

        new_count = await db.fetchval(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"
        )
        return {
            "status": "success",
            "message": f"Schema applied successfully. {new_count} tables created.",
            "tables": new_count,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Schema initialization failed: {e}")


# ===========================================================================
# Schema Introspection
# ===========================================================================
@app.get("/schema/tables", tags=["Schema"])
async def list_tables(request: Request):
    """List all tables in the public schema."""
    db = _get_db(request)
    rows = await db.fetch(
        """
        SELECT table_name,
               (SELECT COUNT(*) FROM information_schema.columns c
                WHERE c.table_name = t.table_name AND c.table_schema = 'public') AS column_count
        FROM information_schema.tables t
        WHERE t.table_schema = 'public' AND t.table_type = 'BASE TABLE'
        ORDER BY t.table_name
        """
    )
    return {
        "total": len(rows),
        "tables": [dict(r) for r in rows],
    }


@app.get("/schema/tables/{table_name}", tags=["Schema"])
async def describe_table(table_name: str, request: Request):
    """Describe columns of a specific table."""
    db = _get_db(request)

    # Validate table exists
    exists = await db.fetchval(
        "SELECT EXISTS(SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name=$1)",
        table_name,
    )
    if not exists:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")

    columns = await db.fetch(
        """
        SELECT column_name, data_type, is_nullable, column_default,
               character_maximum_length
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = $1
        ORDER BY ordinal_position
        """,
        table_name,
    )

    # Get row count
    count = await db.fetchval(f'SELECT COUNT(*) FROM "{table_name}"')

    return {
        "table": table_name,
        "row_count": count,
        "columns": [dict(c) for c in columns],
    }


@app.get("/schema/tables/{table_name}/indexes", tags=["Schema"])
async def list_indexes(table_name: str, request: Request):
    """List indexes on a specific table."""
    db = _get_db(request)
    rows = await db.fetch(
        """
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE schemaname = 'public' AND tablename = $1
        ORDER BY indexname
        """,
        table_name,
    )
    return {"table": table_name, "indexes": [dict(r) for r in rows]}


# ===========================================================================
# Generic CRUD — Query Endpoint
# ===========================================================================
class QueryRequest(BaseModel):
    """Execute a read-only SQL query."""
    sql: str = Field(..., description="SQL query to execute (SELECT only)")
    params: list[Any] | None = Field(default=None, description="Query parameters ($1, $2, ...)")


class MutationRequest(BaseModel):
    """Execute a write SQL statement."""
    sql: str = Field(..., description="SQL statement (INSERT / UPDATE / DELETE)")
    params: list[Any] | None = Field(default=None, description="Statement parameters ($1, $2, ...)")


@app.post("/query", tags=["Query"])
async def execute_query(body: QueryRequest, request: Request):
    """
    Execute a **read-only** SQL query.  
    Only SELECT statements are allowed.
    """
    sql = body.sql.strip()
    if not sql.upper().startswith("SELECT"):
        raise HTTPException(
            status_code=400,
            detail="Only SELECT queries are allowed on this endpoint. Use /execute for mutations.",
        )

    db = _get_db(request)
    try:
        rows = await db.fetch(sql, *(body.params or []))
        return {
            "row_count": len(rows),
            "data": [dict(r) for r in rows],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/execute", tags=["Query"])
async def execute_mutation(body: MutationRequest, request: Request):
    """
    Execute a write SQL statement (INSERT / UPDATE / DELETE).  
    Returns the number of affected rows.
    """
    sql = body.sql.strip()
    blocked = ("DROP ", "TRUNCATE ", "ALTER ", "CREATE ", "GRANT ", "REVOKE ")
    if any(sql.upper().startswith(b) for b in blocked):
        raise HTTPException(
            status_code=403,
            detail="DDL / DCL statements are not allowed through this endpoint.",
        )

    db = _get_db(request)
    try:
        result = await db.execute(sql, *(body.params or []))
        return {"status": "ok", "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ===========================================================================
# Convenience — Users CRUD
# ===========================================================================
class UserCreate(BaseModel):
    email: str
    password_hash: str
    full_name: str
    phone_number: str | None = None
    preferred_currency: str = "INR"


@app.post("/users", tags=["Users"], status_code=201)
async def create_user(user: UserCreate, request: Request):
    """Register a new user."""
    db = _get_db(request)
    try:
        row = await db.fetchrow(
            """
            INSERT INTO users (email, password_hash, full_name, phone_number, preferred_currency)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING user_id, email, full_name, preferred_currency, created_at
            """,
            user.email, user.password_hash, user.full_name,
            user.phone_number, user.preferred_currency,
        )
        return dict(row)
    except asyncpg.UniqueViolationError:
        raise HTTPException(status_code=409, detail="Email already registered")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/users", tags=["Users"])
async def list_users(
    request: Request,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List all users (paginated)."""
    db = _get_db(request)
    rows = await db.fetch(
        """
        SELECT user_id, email, full_name, preferred_currency, is_active, created_at
        FROM users
        ORDER BY created_at DESC
        LIMIT $1 OFFSET $2
        """,
        limit, offset,
    )
    total = await db.fetchval("SELECT COUNT(*) FROM users")
    return {"total": total, "limit": limit, "offset": offset, "users": [dict(r) for r in rows]}


@app.get("/users/{user_id}", tags=["Users"])
async def get_user(user_id: str, request: Request):
    """Get a single user by ID."""
    db = _get_db(request)
    row = await db.fetchrow(
        """
        SELECT user_id, email, full_name, phone_number, preferred_currency,
               locale, timezone, is_active, is_verified, created_at, updated_at
        FROM users WHERE user_id = $1
        """,
        uuid.UUID(user_id),
    )
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return dict(row)


# ===========================================================================
# Convenience — Expenses CRUD
# ===========================================================================
class ExpenseCreate(BaseModel):
    user_id: str
    amount: float
    description: str | None = None
    vendor_name: str | None = None
    category_id: int | None = None
    payment_method_id: int | None = None
    expense_date: str  # YYYY-MM-DD
    source: str = "manual"
    tags: list[str] | None = None
    notes: str | None = None


@app.post("/expenses", tags=["Expenses"], status_code=201)
async def create_expense(expense: ExpenseCreate, request: Request):
    """Create a new expense entry."""
    db = _get_db(request)
    try:
        row = await db.fetchrow(
            """
            INSERT INTO expenses
                (user_id, amount, description, vendor_name, category_id,
                 payment_method_id, expense_date, source, tags, notes)
            VALUES ($1, $2, $3, $4, $5, $6, $7::date, $8, $9, $10)
            RETURNING expense_id, user_id, amount, description, vendor_name,
                      category_id, expense_date, source, created_at
            """,
            uuid.UUID(expense.user_id), expense.amount, expense.description,
            expense.vendor_name, expense.category_id, expense.payment_method_id,
            expense.expense_date, expense.source, expense.tags, expense.notes,
        )
        return dict(row)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/expenses", tags=["Expenses"])
async def list_expenses(
    request: Request,
    user_id: str | None = None,
    category_id: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    source: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
):
    """List expenses with optional filters."""
    db = _get_db(request)

    conditions = ["is_deleted = FALSE"]
    params: list[Any] = []
    idx = 1

    if user_id:
        conditions.append(f"user_id = ${idx}")
        params.append(uuid.UUID(user_id))
        idx += 1
    if category_id:
        conditions.append(f"category_id = ${idx}")
        params.append(category_id)
        idx += 1
    if start_date:
        conditions.append(f"expense_date >= ${idx}::date")
        params.append(start_date)
        idx += 1
    if end_date:
        conditions.append(f"expense_date <= ${idx}::date")
        params.append(end_date)
        idx += 1
    if source:
        conditions.append(f"source = ${idx}")
        params.append(source)
        idx += 1

    where = " AND ".join(conditions)
    params.extend([limit, offset])

    rows = await db.fetch(
        f"""
        SELECT e.expense_id, e.user_id, e.amount, e.currency, e.description,
               e.vendor_name, e.expense_date, e.source, e.tags,
               c.name AS category_name, e.created_at
        FROM expenses e
        LEFT JOIN categories c ON e.category_id = c.category_id
        WHERE {where}
        ORDER BY e.expense_date DESC, e.created_at DESC
        LIMIT ${idx} OFFSET ${idx + 1}
        """,
        *params,
    )

    return {
        "count": len(rows),
        "limit": limit,
        "offset": offset,
        "expenses": [dict(r) for r in rows],
    }


@app.get("/expenses/{expense_id}", tags=["Expenses"])
async def get_expense(expense_id: str, request: Request):
    """Get a single expense by ID."""
    db = _get_db(request)
    row = await db.fetchrow(
        """
        SELECT e.*, c.name AS category_name, pm.label AS payment_method_label
        FROM expenses e
        LEFT JOIN categories c ON e.category_id = c.category_id
        LEFT JOIN payment_methods pm ON e.payment_method_id = pm.payment_method_id
        WHERE e.expense_id = $1 AND e.is_deleted = FALSE
        """,
        uuid.UUID(expense_id),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Expense not found")
    return dict(row)


@app.delete("/expenses/{expense_id}", tags=["Expenses"])
async def delete_expense(expense_id: str, request: Request):
    """Soft-delete an expense."""
    db = _get_db(request)
    result = await db.execute(
        "UPDATE expenses SET is_deleted = TRUE, updated_at = NOW() WHERE expense_id = $1",
        uuid.UUID(expense_id),
    )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Expense not found")
    return {"status": "deleted", "expense_id": expense_id}


# ===========================================================================
# Convenience — Categories
# ===========================================================================
@app.get("/categories", tags=["Categories"])
async def list_categories(request: Request, user_id: str | None = None):
    """List all categories (system defaults + user-defined)."""
    db = _get_db(request)

    if user_id:
        rows = await db.fetch(
            """
            SELECT * FROM categories
            WHERE is_system_default = TRUE OR user_id = $1
            ORDER BY is_system_default DESC, name
            """,
            uuid.UUID(user_id),
        )
    else:
        rows = await db.fetch(
            "SELECT * FROM categories WHERE is_system_default = TRUE ORDER BY name"
        )

    return {"total": len(rows), "categories": [dict(r) for r in rows]}


# ===========================================================================
# Convenience — Budgets
# ===========================================================================
class BudgetCreate(BaseModel):
    user_id: str
    category_id: int | None = None
    amount: float
    budget_type: str = "monthly"
    start_date: str
    end_date: str | None = None
    alert_threshold: float = 80.0


@app.post("/budgets", tags=["Budgets"], status_code=201)
async def create_budget(budget: BudgetCreate, request: Request):
    """Create a budget for a user."""
    db = _get_db(request)
    row = await db.fetchrow(
        """
        INSERT INTO budgets (user_id, category_id, amount, budget_type, start_date, end_date, alert_threshold)
        VALUES ($1, $2, $3, $4, $5::date, $6::date, $7)
        RETURNING *
        """,
        uuid.UUID(budget.user_id), budget.category_id, budget.amount,
        budget.budget_type, budget.start_date, budget.end_date, budget.alert_threshold,
    )
    return dict(row)


@app.get("/budgets/{user_id}", tags=["Budgets"])
async def get_user_budgets(user_id: str, request: Request):
    """Get all budgets for a user."""
    db = _get_db(request)
    rows = await db.fetch(
        """
        SELECT b.*, c.name AS category_name
        FROM budgets b
        LEFT JOIN categories c ON b.category_id = c.category_id
        WHERE b.user_id = $1 AND b.is_active = TRUE
        ORDER BY b.created_at DESC
        """,
        uuid.UUID(user_id),
    )
    return {"total": len(rows), "budgets": [dict(r) for r in rows]}


# ===========================================================================
# Analytics / Dashboard Endpoints
# ===========================================================================
@app.get("/analytics/summary/{user_id}", tags=["Analytics"])
async def spending_summary(
    user_id: str,
    request: Request,
    start_date: str | None = None,
    end_date: str | None = None,
):
    """Get spending summary for a user in a date range."""
    db = _get_db(request)

    uid = uuid.UUID(user_id)

    # Total spending
    total = await db.fetchrow(
        """
        SELECT COALESCE(SUM(amount), 0) AS total_spent,
               COUNT(*) AS transaction_count,
               COALESCE(AVG(amount), 0) AS avg_transaction
        FROM expenses
        WHERE user_id = $1 AND is_deleted = FALSE
          AND ($2::date IS NULL OR expense_date >= $2::date)
          AND ($3::date IS NULL OR expense_date <= $3::date)
        """,
        uid, start_date, end_date,
    )

    # By category
    by_category = await db.fetch(
        """
        SELECT c.name AS category, c.icon, c.color,
               COALESCE(SUM(e.amount), 0) AS total,
               COUNT(*) AS count
        FROM expenses e
        JOIN categories c ON e.category_id = c.category_id
        WHERE e.user_id = $1 AND e.is_deleted = FALSE
          AND ($2::date IS NULL OR e.expense_date >= $2::date)
          AND ($3::date IS NULL OR e.expense_date <= $3::date)
        GROUP BY c.category_id, c.name, c.icon, c.color
        ORDER BY total DESC
        """,
        uid, start_date, end_date,
    )

    # Daily trend
    daily_trend = await db.fetch(
        """
        SELECT expense_date, SUM(amount) AS daily_total, COUNT(*) AS count
        FROM expenses
        WHERE user_id = $1 AND is_deleted = FALSE
          AND ($2::date IS NULL OR expense_date >= $2::date)
          AND ($3::date IS NULL OR expense_date <= $3::date)
        GROUP BY expense_date
        ORDER BY expense_date
        """,
        uid, start_date, end_date,
    )

    return {
        "user_id": user_id,
        "period": {"start": start_date, "end": end_date},
        "summary": dict(total),
        "by_category": [dict(r) for r in by_category],
        "daily_trend": [dict(r) for r in daily_trend],
    }


@app.get("/analytics/top-vendors/{user_id}", tags=["Analytics"])
async def top_vendors(
    user_id: str,
    request: Request,
    limit: int = Query(default=10, le=50),
):
    """Get top vendors by spending for a user."""
    db = _get_db(request)
    rows = await db.fetch(
        """
        SELECT vendor_name, SUM(amount) AS total_spent, COUNT(*) AS visit_count
        FROM expenses
        WHERE user_id = $1 AND is_deleted = FALSE AND vendor_name IS NOT NULL
        GROUP BY vendor_name
        ORDER BY total_spent DESC
        LIMIT $2
        """,
        uuid.UUID(user_id), limit,
    )
    return {"user_id": user_id, "top_vendors": [dict(r) for r in rows]}


# ===========================================================================
# Database Stats (admin)
# ===========================================================================
@app.get("/stats", tags=["System"])
async def database_stats(request: Request):
    """Get database statistics."""
    db = _get_db(request)

    tables = await db.fetch(
        """
        SELECT t.table_name,
               pg_total_relation_size(quote_ident(t.table_name)) AS total_bytes,
               pg_size_pretty(pg_total_relation_size(quote_ident(t.table_name))) AS size,
               (SELECT n_live_tup FROM pg_stat_user_tables st
                WHERE st.relname = t.table_name) AS estimated_rows
        FROM information_schema.tables t
        WHERE t.table_schema = 'public' AND t.table_type = 'BASE TABLE'
        ORDER BY pg_total_relation_size(quote_ident(t.table_name)) DESC
        """
    )

    db_size = await db.fetchval("SELECT pg_size_pretty(pg_database_size(current_database()))")

    return {
        "database_size": db_size,
        "table_count": len(tables),
        "tables": [dict(t) for t in tables],
    }
