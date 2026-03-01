# ============================================================================
# Expense Manager — Simplified FastAPI (College Project)
# 4 tables: users, categories, expenses, budgets
# Serves API + Frontend from a single server
# ============================================================================
from __future__ import annotations

import pathlib
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import asyncpg
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.database import DatabasePool

FRONTEND_DIR = pathlib.Path(__file__).parent.parent / "frontend"


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(application: FastAPI):
    application.state.db = DatabasePool()
    await application.state.db.connect()
    yield
    await application.state.db.disconnect()


app = FastAPI(
    title="💰 Expense Manager API",
    description="Simple expense tracker API — college project",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _db(request: Request) -> DatabasePool:
    return request.app.state.db


# ===========================================================================
# Health
# ===========================================================================
@app.get("/health", tags=["System"])
async def health():
    return {"status": "healthy", "ts": datetime.now(timezone.utc).isoformat()}


# ===========================================================================
# Schema Init
# ===========================================================================
@app.post("/schema/init", tags=["System"])
async def init_schema(request: Request):
    """Apply schema.sql to set up the database tables."""
    db = _db(request)
    schema_path = pathlib.Path(__file__).parent.parent / "schema" / "schema.sql"
    if not schema_path.exists():
        raise HTTPException(500, "schema.sql not found")
    sql = schema_path.read_text(encoding="utf-8")
    try:
        async with db._pool.acquire() as conn:
            await conn.execute(sql)
        return {"status": "ok", "message": "Schema applied"}
    except Exception as e:
        raise HTTPException(500, f"Schema error: {e}")


# ===========================================================================
# Users
# ===========================================================================
class UserCreate(BaseModel):
    email: str
    full_name: str
    preferred_currency: str = "INR"


@app.post("/users", tags=["Users"], status_code=201)
async def create_user(body: UserCreate, request: Request):
    db = _db(request)
    try:
        row = await db.fetchrow(
            "INSERT INTO users (email, full_name, preferred_currency) "
            "VALUES ($1, $2, $3) RETURNING *",
            body.email, body.full_name, body.preferred_currency,
        )
        return dict(row)
    except asyncpg.UniqueViolationError:
        raise HTTPException(409, "Email already exists")


@app.get("/users", tags=["Users"])
async def list_users(request: Request, limit: int = 50, offset: int = 0):
    db = _db(request)
    rows = await db.fetch(
        "SELECT user_id, email, full_name, preferred_currency, created_at "
        "FROM users ORDER BY created_at DESC LIMIT $1 OFFSET $2",
        limit, offset,
    )
    total = await db.fetchval("SELECT COUNT(*) FROM users")
    return {"total": total, "users": [dict(r) for r in rows]}


@app.get("/users/{user_id}", tags=["Users"])
async def get_user(user_id: str, request: Request):
    db = _db(request)
    row = await db.fetchrow("SELECT * FROM users WHERE user_id = $1", uuid.UUID(user_id))
    if not row:
        raise HTTPException(404, "User not found")
    return dict(row)


class UserUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None
    avatar: str | None = None
    preferred_currency: str | None = None
    dark_mode: bool | None = None


@app.put("/users/{user_id}/profile", tags=["Users"])
async def update_user_profile(user_id: str, body: UserUpdate, request: Request):
    db = _db(request)
    user_uuid = uuid.UUID(user_id)
    row = await db.fetchrow("SELECT * FROM users WHERE user_id = $1", user_uuid)
    if not row:
        raise HTTPException(404, "User not found")

    new_full_name = body.full_name if body.full_name is not None else row["full_name"]
    new_email = body.email if body.email is not None else row["email"]
    new_avatar = body.avatar if body.avatar is not None else row["avatar"]
    new_currency = body.preferred_currency if body.preferred_currency is not None else row["preferred_currency"]
    new_dark_mode = body.dark_mode if body.dark_mode is not None else row["dark_mode"]

    try:
        updated = await db.fetchrow(
            """
            UPDATE users 
            SET full_name = $1, email = $2, avatar = $3, preferred_currency = $4, dark_mode = $5
            WHERE user_id = $6 RETURNING *
            """,
            new_full_name, new_email, new_avatar, new_currency, new_dark_mode, user_uuid
        )
        return dict(updated)
    except asyncpg.UniqueViolationError:
        raise HTTPException(409, "Email already exists")


# ===========================================================================
# Categories
# ===========================================================================
@app.get("/categories", tags=["Categories"])
async def list_categories(request: Request):
    db = _db(request)
    rows = await db.fetch("SELECT * FROM categories ORDER BY category_id")
    return {"total": len(rows), "categories": [dict(r) for r in rows]}


# ===========================================================================
# Expenses
# ===========================================================================
class ExpenseCreate(BaseModel):
    user_id: str
    amount: float
    category_id: int | None = None
    expense_date: str  # YYYY-MM-DD


@app.post("/expenses", tags=["Expenses"], status_code=201)
async def create_expense(body: ExpenseCreate, request: Request):
    db = _db(request)
    try:
        import datetime
        dt = datetime.datetime.strptime(body.expense_date, "%Y-%m-%d").date()
        row = await db.fetchrow(
            "INSERT INTO expenses (user_id, amount, category_id, expense_date) "
            "VALUES ($1, $2, $3, $4) RETURNING *",
            uuid.UUID(body.user_id), body.amount, body.category_id, dt,
        )
        return dict(row)
    except Exception as e:
        raise HTTPException(400, str(e))


@app.get("/expenses", tags=["Expenses"])
async def list_expenses(
    request: Request,
    user_id: str | None = None,
    category_id: int | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
):
    db = _db(request)
    conditions = []
    params: list[Any] = []
    idx = 1

    if user_id:
        conditions.append(f"e.user_id = ${idx}")
        params.append(uuid.UUID(user_id))
        idx += 1
    if category_id:
        conditions.append(f"e.category_id = ${idx}")
        params.append(category_id)
        idx += 1

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    params.extend([limit, offset])

    rows = await db.fetch(
        f"""
        SELECT e.expense_id, e.user_id, e.amount, e.category_id,
               e.expense_date,
               c.name AS category_name, c.icon AS category_icon, c.color AS category_color,
               e.created_at
        FROM expenses e
        LEFT JOIN categories c ON e.category_id = c.category_id
        {where}
        ORDER BY e.expense_date DESC, e.created_at DESC
        LIMIT ${idx} OFFSET ${idx + 1}
        """,
        *params,
    )
    return {"count": len(rows), "expenses": [dict(r) for r in rows]}


@app.delete("/expenses/{expense_id}", tags=["Expenses"])
async def delete_expense(expense_id: str, request: Request):
    db = _db(request)
    result = await db.execute(
        "DELETE FROM expenses WHERE expense_id = $1", uuid.UUID(expense_id)
    )
    if result == "DELETE 0":
        raise HTTPException(404, "Not found")
    return {"status": "deleted"}


# ===========================================================================
# Budgets
# ===========================================================================
class BudgetCreate(BaseModel):
    user_id: str
    category_id: int | None = None
    amount: float
    month: str  # e.g. '2026-02'


@app.post("/budgets", tags=["Budgets"], status_code=201)
async def create_budget(body: BudgetCreate, request: Request):
    db = _db(request)
    row = await db.fetchrow(
        "INSERT INTO budgets (user_id, category_id, amount, month) "
        "VALUES ($1, $2, $3, $4) "
        "ON CONFLICT (user_id, category_id, month) DO UPDATE SET amount = $3 "
        "RETURNING *",
        uuid.UUID(body.user_id), body.category_id, body.amount, body.month,
    )
    return dict(row)


@app.get("/budgets/{user_id}", tags=["Budgets"])
async def get_budgets(user_id: str, request: Request, month: str | None = None):
    db = _db(request)
    if month:
        rows = await db.fetch(
            "SELECT b.*, c.name AS category_name, c.icon AS category_icon "
            "FROM budgets b LEFT JOIN categories c ON b.category_id = c.category_id "
            "WHERE b.user_id = $1 AND b.month = $2 ORDER BY b.budget_id",
            uuid.UUID(user_id), month,
        )
    else:
        rows = await db.fetch(
            "SELECT b.*, c.name AS category_name, c.icon AS category_icon "
            "FROM budgets b LEFT JOIN categories c ON b.category_id = c.category_id "
            "WHERE b.user_id = $1 ORDER BY b.month DESC, b.budget_id",
            uuid.UUID(user_id),
        )
    return {"total": len(rows), "budgets": [dict(r) for r in rows]}


# ===========================================================================
# Analytics (simple summary)
# ===========================================================================
@app.get("/analytics/summary/{user_id}", tags=["Analytics"])
async def spending_summary(user_id: str, request: Request, start_date: str | None = None, end_date: str | None = None):
    db = _db(request)
    uid = uuid.UUID(user_id)
    import datetime

    # Base WHERE clause
    where = "WHERE user_id = $1"
    params = [uid]

    if start_date:
        try:
            sd_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
            where += f" AND expense_date >= ${len(params)+1}"
            params.append(sd_dt)
        except: pass
    if end_date:
        try:
            ed_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
            where += f" AND expense_date <= ${len(params)+1}"
            params.append(ed_dt)
        except: pass

    summary = await db.fetchrow(
        f"SELECT COALESCE(SUM(amount),0) AS total_spent, "
        f"COUNT(*) AS transaction_count, "
        f"COALESCE(AVG(amount),0) AS avg_transaction "
        f"FROM expenses {where}",
        *params
    )

    by_category = await db.fetch(
        f"SELECT c.name AS category, c.icon, c.color, "
        f"SUM(e.amount) AS total, COUNT(*) AS count "
        f"FROM expenses e JOIN categories c ON e.category_id = c.category_id "
        f"{where.replace('expense_date', 'e.expense_date')} "
        f"GROUP BY c.category_id, c.name, c.icon, c.color "
        f"ORDER BY total DESC",
        *params
    )

    daily_trend = await db.fetch(
        f"SELECT expense_date, SUM(amount) AS daily_total "
        f"FROM expenses {where} "
        f"GROUP BY expense_date ORDER BY expense_date DESC LIMIT 30",
        *params
    )

    return {
        "user_id": user_id,
        "summary": dict(summary),
        "by_category": [dict(r) for r in by_category],
        "daily_trend": [dict(r) for r in daily_trend],
    }


# ===========================================================================
# Chatbot (imports from app/chatbot.py)
# ===========================================================================
class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    user_id: str
    history: list[ChatMessage] = []


@app.post("/chatbot", tags=["Chatbot"])
async def chatbot_endpoint(body: ChatRequest, request: Request):
    """AI chatbot — uses LangChain + Cerebras to answer expense questions."""
    import os
    api_key = os.getenv("CEREBRAS_API_KEY", "")
    if not api_key:
        raise HTTPException(500, "CEREBRAS_API_KEY not set")

    db = _db(request)
    try:
        from app.chatbot import run_chat
        history_list = [h.model_dump() for h in body.history]
        reply = await run_chat(db, body.user_id, body.message, api_key, history=history_list)
        return {"reply": reply}
    except Exception:
        # Silent fallback for chatbot errors in production
        return {"reply": "I'm sorry, I'm having trouble thinking clearly right now. Please try again in a bit! 🧠💤"}


# ===========================================================================
# Frontend — Serve at root
# ===========================================================================
if FRONTEND_DIR.exists():
    app.mount("/_assets", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")


@app.get("/", include_in_schema=False)
async def serve_root():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")
