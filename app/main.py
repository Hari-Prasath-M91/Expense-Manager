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
from fastapi import FastAPI, HTTPException, Query, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
import os
import httpx

from app.database import DatabasePool
from app.config import settings
from app.gmail import fetch_gmail_expenses
from app.recommendations import get_ai_recommendations

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
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

# OAuth Setup
oauth = OAuth()
oauth.register(
    name='google',
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile https://www.googleapis.com/auth/gmail.readonly'}
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
# Auth
# ===========================================================================
@app.get("/auth/google", tags=["Auth"])
async def login_google(request: Request):
    """Initiate Google OAuth login."""
    redirect_uri = request.url_for('auth_callback')
    # If served behind HTTPS (like on Render), ensure redirect_uri uses https
    if "render.com" in str(redirect_uri) or os.getenv("RENDER"):
         redirect_uri = str(redirect_uri).replace("http://", "https://")
    return await oauth.google.authorize_redirect(
        request, 
        str(redirect_uri), 
        access_type='offline', 
        prompt='consent'
    )


@app.get("/auth/callback", name="auth_callback", tags=["Auth"])
async def auth_callback(request: Request):
    """Handle Google OAuth callback."""
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(400, f"OAuth error: {e}")

    user_info = token.get('userinfo')
    if not user_info:
        raise HTTPException(400, "Failed to get user info from Google")

    db = _db(request)
    # Check if user exists by google_id or email
    row = await db.fetchrow(
        "SELECT * FROM users WHERE google_id = $1 OR email = $2",
        user_info['sub'], user_info['email']
    )

    if row:
        # Update existing user (sync name/avatar if needed)
        updated = await db.fetchrow(
            """
            UPDATE users 
            SET full_name = $1, avatar = $2, google_id = $3
            WHERE user_id = $4 RETURNING *
            """,
            user_info.get('name', row['full_name']),
            user_info.get('picture', row['avatar']),
            user_info['sub'],
            row['user_id']
        )
        user_data = dict(updated)
    else:
        # Create new user
        new_user = await db.fetchrow(
            """
            INSERT INTO users (google_id, email, full_name, avatar)
            VALUES ($1, $2, $3, $4) RETURNING *
            """,
            user_info['sub'], user_info['email'], 
            user_info.get('name', 'User'), user_info.get('picture')
        )
        user_data = dict(new_user)

    # Save refresh token if provided
    refresh_token = token.get('refresh_token')
    if refresh_token:
        await db.execute(
            "UPDATE users SET google_refresh_token = $1 WHERE user_id = $2",
            refresh_token, user_data['user_id']
        )

    # Redirect to frontend with user_id in hash or query
    request.session['google_token'] = token
    return RedirectResponse(url=f"/#login_success?user_id={user_data['user_id']}")
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
    description: str | None = None
    expense_date: str  # YYYY-MM-DD


@app.post("/expenses", tags=["Expenses"], status_code=201)
async def create_expense(body: ExpenseCreate, request: Request):
    db = _db(request)
    try:
        import datetime
        dt = datetime.datetime.strptime(body.expense_date, "%Y-%m-%d").date()
        row = await db.fetchrow(
            "INSERT INTO expenses (user_id, amount, category_id, description, expense_date) "
            "VALUES ($1, $2, $3, $4, $5) RETURNING *",
            uuid.UUID(body.user_id), body.amount, body.category_id, body.description, dt,
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
               e.description, e.expense_date,
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


@app.get("/analytics/recommendations/{user_id}", tags=["Analytics"])
async def ai_recommendations(user_id: str, request: Request):
    """Get personalized AI recommendations for the user."""
    db = _db(request)
    api_key = settings.cerebras_api_key or os.getenv("CEREBRAS_API_KEY", "")
    if not api_key:
        raise HTTPException(500, "CEREBRAS_API_KEY not set")
    
    try:
        recommendations = await get_ai_recommendations(db, user_id, api_key)
        return recommendations
    except Exception as e:
        raise HTTPException(500, str(e))


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


async def _get_valid_google_token(request: Request, user_id: str) -> str | None:
    """Helper to get a valid access token, refreshing if necessary."""
    token_data = request.session.get('google_token')
    if token_data and 'access_token' in token_data:
        # Check if already expired (with 10s buffer)
        expires_at = token_data.get('expires_at', 0)
        if expires_at > datetime.now().timestamp() + 10:
            return token_data['access_token']

    # Try to refresh
    db = _db(request)
    row = await db.fetchrow("SELECT google_refresh_token FROM users WHERE user_id = $1", uuid.UUID(user_id))
    if not row or not row['google_refresh_token']:
        return None

    # Google Token Refresh API
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "refresh_token": row['google_refresh_token'],
                    "grant_type": "refresh_token",
                }
            )
            if resp.status_code == 200:
                new_token = resp.json()
                # Update session
                curr_token = request.session.get('google_token', {})
                curr_token.update(new_token)
                request.session['google_token'] = curr_token
                return new_token['access_token']
    except Exception as e:
        print(f"Token refresh failed: {e}")

    return None


@app.get("/sync/gmail/preview", tags=["Gmail"])
async def preview_gmail_sync(request: Request, user_id: str):
    """Fetch potential expenses from Gmail (preview only)."""
    db = _db(request)
    uid = uuid.UUID(user_id)
    
    # Get already synced/scanned IDs for this user
    rows = await db.fetch("SELECT msg_id FROM gmail_scanned_ids WHERE user_id = $1", uid)
    existing_ids = [r['msg_id'] for r in rows]
    
    # Get user preferred currency
    user_row = await db.fetchrow("SELECT preferred_currency FROM users WHERE user_id = $1", uid)
    user_currency = user_row['preferred_currency'] if user_row else 'INR'

    access_token = await _get_valid_google_token(request, user_id)
    if not access_token:
        raise HTTPException(401, "Google session expired. Please log in again to reconnect.")

    cerebras_key = settings.cerebras_api_key or os.getenv("CEREBRAS_API_KEY", "")
    if not cerebras_key:
        raise HTTPException(500, "AI Service not configured")

    try:
        new_expenses, all_scanned_ids = await fetch_gmail_expenses(access_token, cerebras_key, existing_ids)
        
        # Currency Conversion
        fx_rates = {}
        async with httpx.AsyncClient() as client:
            try:
                # Cache user base rate
                fx_res = await client.get(f"https://open.er-api.com/v6/latest/{user_currency}")
                if fx_res.status_code == 200:
                    fx_rates = fx_res.json().get("rates", {})
            except: pass

        for exp in new_expenses:
            orig_curr = exp.get("currency", "INR").upper()
            if orig_curr != user_currency and fx_rates:
                # Convert to User Currency
                # Rate is: 1 Base (UserCurr) = X OrigCurr. 
                # So WorkAmount = OrigAmount / Rate
                rate = fx_rates.get(orig_curr)
                if rate and rate > 0:
                    exp["original_amount"] = exp["amount"]
                    exp["original_currency"] = orig_curr
                    exp["amount"] = round(float(exp["amount"]) / float(rate), 2)
                    exp["currency"] = user_currency
                    exp["converted"] = True
            else:
                exp["currency"] = user_currency

        return {
            "status": "ok", 
            "expenses": new_expenses,
            "scanned_ids": all_scanned_ids 
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Gmail Preview failed: {str(e)}")


@app.post("/sync/gmail/confirm", tags=["Gmail"])
async def confirm_gmail_sync(request: Request, user_id: str, body: dict):
    """Save user-approved expenses and mark all batch IDs as scanned."""
    db = _db(request)
    uid = uuid.UUID(user_id)
    
    expenses = body.get("expenses", []) or []
    scanned_ids = body.get("scanned_ids", []) or []
    
    saved_count = 0
    # 1. Save approved expenses
    for exp in expenses:
        try:
            cat_row = await db.fetchrow(
                "SELECT category_id FROM categories WHERE LOWER(name) = LOWER($1) LIMIT 1",
                exp.get('category', 'Others')
            )
            cat_id = cat_row['category_id'] if cat_row else 6 
            
            raw_date = exp.get('expense_date')
            exp_date = datetime.strptime(raw_date, "%Y-%m-%d").date() if raw_date else datetime.now().date()

            await db.execute(
                "INSERT INTO expenses (user_id, amount, category_id, description, expense_date, gmail_msg_id) VALUES ($1, $2, $3, $4, $5, $6)",
                uid, float(exp['amount']), cat_id, exp.get('description'), exp_date, exp.get('msg_id')
            )
            saved_count += 1
        except Exception: 
            continue
            
    # 2. Mark all IDs as scanned so they never reappear
    if scanned_ids:
        try:
            await db.execute(
                "INSERT INTO gmail_scanned_ids (msg_id, user_id) "
                "SELECT unnest($1::varchar[]), $2 "
                "ON CONFLICT (msg_id) DO NOTHING",
                scanned_ids, uid
            )
        except Exception as e:
            print(f"Error marking scanned IDs: {e}")

    return {"status": "ok", "count": saved_count, "message": f"Successfully synced {saved_count} expenses."}


# ===========================================================================
# OCR — Invoice Processing
# ===========================================================================
@app.post("/ocr/upload", tags=["OCR"])
async def ocr_upload(file: UploadFile = File(...)):
    """Upload an invoice/receipt image, OCR it, and return structured items."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "File must be an image (JPG, PNG, etc.)")

    image_bytes = await file.read()
    cerebras_key = settings.cerebras_api_key or os.getenv("CEREBRAS_API_KEY", "")

    try:
        from app.ocr import process_receipt
        result = process_receipt(image_bytes, cerebras_key)
        return {"status": "ok", **result}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"OCR processing failed: {str(e)}")


class OCRSaveItem(BaseModel):
    description: str | None = None
    amount: float
    category_id: int | None = None
    expense_date: str  # YYYY-MM-DD


class OCRSaveRequest(BaseModel):
    user_id: str
    items: list[OCRSaveItem]


@app.post("/ocr/save", tags=["OCR"])
async def ocr_save(body: OCRSaveRequest, request: Request):
    """Batch-save OCR-extracted expense items."""
    db = _db(request)
    uid = uuid.UUID(body.user_id)
    saved = 0
    import datetime as dt_mod
    for item in body.items:
        try:
            exp_date = dt_mod.datetime.strptime(item.expense_date, "%Y-%m-%d").date()
            await db.execute(
                "INSERT INTO expenses (user_id, amount, category_id, description, expense_date) "
                "VALUES ($1, $2, $3, $4, $5)",
                uid, item.amount, item.category_id, item.description, exp_date,
            )
            saved += 1
        except Exception as e:
            print(f"OCR save error: {e}")
            continue
    return {"status": "ok", "count": saved, "message": f"Saved {saved} expenses."}


if FRONTEND_DIR.exists():
    app.mount("/_assets", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")

@app.get("/", include_in_schema=False)
async def serve_root():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return RedirectResponse(url="/docs")
