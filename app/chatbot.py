# ============================================================================
# Chatbot — LangChain + Cerebras(GPT-OSS-120b)
# Tools that query the database directly for expense insights
# ============================================================================
from __future__ import annotations

import json
import uuid

from app.database import DatabasePool


# ---------------------------------------------------------------------------
# Database query helpers (tools for the LLM)
# ---------------------------------------------------------------------------
async def _get_total_spending(db: DatabasePool, uid: uuid.UUID, **kwargs) -> str:
    """Get total spending for this user."""
    currency = kwargs.get('currency', '₹')
    row = await db.fetchrow(
        "SELECT COALESCE(SUM(amount),0) AS total, COUNT(*) AS count, "
        "COALESCE(AVG(amount),0) AS avg FROM expenses WHERE user_id = $1",
        uid,
    )
    r = dict(row)
    return (
        f"Total spent: {currency} {r['total']:.0f} across {r['count']} transactions. "
        f"Average per transaction: {currency} {r['avg']:.0f}."
    )


async def _get_category_breakdown(db: DatabasePool, uid: uuid.UUID, **kwargs) -> str:
    """Get spending breakdown by category."""
    currency = kwargs.get('currency', '₹')
    rows = await db.fetch(
        "SELECT c.name, c.icon, SUM(e.amount) AS total, COUNT(*) AS count "
        "FROM expenses e JOIN categories c ON e.category_id = c.category_id "
        "WHERE e.user_id = $1 GROUP BY c.name, c.icon ORDER BY total DESC",
        uid,
    )
    if not rows:
        return "No expenses found. The user hasn't recorded any spending yet."
    lines = [f"  {dict(r)['icon']} {dict(r)['name']}: {currency} {dict(r)['total']:.0f} ({dict(r)['count']} txns)" for r in rows]
    return "Spending by category:\n" + "\n".join(lines)


async def _get_recent_expenses(db: DatabasePool, uid: uuid.UUID, **kwargs) -> str:
    """Get the 10 most recent expenses."""
    currency = kwargs.get('currency', '₹')
    rows = await db.fetch(
        "SELECT e.amount, e.expense_date, "
        "c.name AS category FROM expenses e "
        "LEFT JOIN categories c ON e.category_id = c.category_id "
        "WHERE e.user_id = $1 ORDER BY e.expense_date DESC LIMIT 10",
        uid,
    )
    if not rows:
        return "No recent expenses found."
    lines = []
    for r in rows:
        d = dict(r)
        lines.append(f"  {currency} {d['amount']:.0f} - ({d.get('category', 'Uncategorized')}) on {d['expense_date']}")
    return "Recent expenses:\n" + "\n".join(lines)


async def _get_budget_status(db: DatabasePool, uid: uuid.UUID, **kwargs) -> str:
    """Get budget vs actual spending for current month."""
    currency = kwargs.get('currency', '₹')
    from datetime import datetime
    month = datetime.now().strftime("%Y-%m")
    budgets = await db.fetch(
        "SELECT b.amount AS budget, c.name AS category, c.icon "
        "FROM budgets b LEFT JOIN categories c ON b.category_id = c.category_id "
        "WHERE b.user_id = $1 AND b.month = $2",
        uid, month,
    )
    if not budgets:
        return f"No budgets set for {month}."

    lines = []
    for b in budgets:
        bd = dict(b)
        cat_name = bd.get("category") or "Overall"
        # Get actual spending for this category this month
        spent = await db.fetchval(
            "SELECT COALESCE(SUM(amount),0) FROM expenses "
            "WHERE user_id = $1 AND category_id = (SELECT category_id FROM categories WHERE name = $2) "
            "AND expense_date >= $3 || '-01'",
            uid, cat_name, month,
        ) or 0
        remaining = bd["budget"] - float(spent)
        status = "✅ Under" if remaining >= 0 else "🚨 OVER"
        lines.append(f"  {bd.get('icon','')} {cat_name}: {currency} {spent:.0f} / {currency} {bd['budget']:.0f} ({status} by {currency} {abs(remaining):.0f})")
    return f"Budget status for {month}:\n" + "\n".join(lines)


async def _get_daily_trend(db: DatabasePool, uid: uuid.UUID, **kwargs) -> str:
    """Get daily spending trend for the last 7 days."""
    currency = kwargs.get('currency', '₹')
    rows = await db.fetch(
        "SELECT expense_date, SUM(amount) AS total "
        "FROM expenses WHERE user_id = $1 "
        "AND expense_date >= CURRENT_DATE - INTERVAL '7 days' "
        "GROUP BY expense_date ORDER BY expense_date",
        uid,
    )
    if not rows:
        return "No spending in the last 7 days."
    lines = [f"  {dict(r)['expense_date']}: {currency} {dict(r)['total']:.0f}" for r in rows]
    return "Daily spending (last 7 days):\n" + "\n".join(lines)


async def _add_expense(db: DatabasePool, uid: uuid.UUID, amount: float, category_name: str, expense_date: str, **kwargs) -> str:
    """Add a new expense for the user."""
    currency = kwargs.get('currency', '₹')
    from datetime import datetime
    try:
        # 1. Normalize category
        cat_row = await db.fetchrow(
            "SELECT category_id, name FROM categories WHERE LOWER(name) = LOWER($1) LIMIT 1",
            category_name.strip()
        )
        if not cat_row:
            # Fallback: try to find a category that contains the name
            cat_row = await db.fetchrow(
                "SELECT category_id, name FROM categories WHERE LOWER(name) LIKE LOWER($1) LIMIT 1",
                f"%{category_name.strip()}%"
            )
        
        if not cat_row:
            return f"Error: Category '{category_name}' not found. Please specify Food, Travel, Shopping, Bills, or Others."

        cat_id = cat_row['category_id']
        actual_cat_name = cat_row['name']

        # 2. Parse date
        try:
            dt = datetime.strptime(expense_date.strip(), "%Y-%m-%d").date()
        except ValueError:
            return f"Error: Invalid date format '{expense_date}'. Please use YYYY-MM-DD."

        # 3. Insert
        await db.execute(
            "INSERT INTO expenses (user_id, amount, category_id, expense_date) VALUES ($1, $2, $3, $4)",
            uid, float(amount), cat_id, dt
        )
        return f"Successfully recorded: {currency} {amount:.0f} for {actual_cat_name} on {expense_date}."
    except Exception as e:
        return f"Failed to add expense: {str(e)}"


# ---------------------------------------------------------------------------
# Tool definitions for the LLM
# ---------------------------------------------------------------------------
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_total_spending",
            "description": "Get the user's total spending, transaction count, and average transaction amount",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_category_breakdown",
            "description": "Get spending breakdown by category (food, travel, shopping, etc.)",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_expenses",
            "description": "Get the 10 most recent expense transactions",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_budget_status",
            "description": "Get budget vs actual spending status for the current month",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_daily_trend",
            "description": "Get daily spending trend for the last 7 days",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_expense",
            "description": "Add/record a new expense for the user",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {"type": "number", "description": "The amount spent"},
                    "category_name": {"type": "string", "description": "Category: Food, Transport, Shopping, Bills, Entertainment, Others"},
                    "expense_date": {"type": "string", "description": "Date in YYYY-MM-DD format"}
                },
                "required": ["amount", "category_name", "expense_date"],
            },
        },
    },
]

TOOL_MAP = {
    "get_total_spending": _get_total_spending,
    "get_category_breakdown": _get_category_breakdown,
    "get_recent_expenses": _get_recent_expenses,
    "get_budget_status": _get_budget_status,
    "get_daily_trend": _get_daily_trend,
    "add_expense": _add_expense,
}

SYSTEM_PROMPT = """You are a helpful AI financial assistant for a personal expense tracking app.
Today is {today}.
The user's preferred currency is {currency}.
You have tools to query and record the user's real expense data from their database.

Guidelines:
- Use the tools to fetch data OR record new expenses if the user asks (e.g., 'I spent 500 on lunch today')
- Be concise and friendly with your responses
- Always mention amounts with the correct currency symbol ({currency})
- Give actionable financial tips when relevant
- Keep responses under 150 words"""


# ---------------------------------------------------------------------------
# Main chat function (tool-calling loop)
# ---------------------------------------------------------------------------
async def run_chat(db: DatabasePool, user_id: str, message: str, api_key: str, history: list[dict] | None = None) -> str:
    """Run the chatbot with tool-calling using Cerebras."""
    from datetime import datetime
    from cerebras.cloud.sdk import Cerebras
    try:
        client = Cerebras(api_key=api_key)
        uid = uuid.UUID(user_id)
        
        # Get user preferred currency
        user_row = await db.fetchrow("SELECT preferred_currency FROM users WHERE user_id = $1", uid)
        currency = user_row['preferred_currency'] if user_row else '₹'

        # Inject today's date
        current_date_str = datetime.now().strftime("%A, %B %d, %Y")
        prompt = SYSTEM_PROMPT.format(today=current_date_str, currency=currency)

        messages = [
            {"role": "system", "content": prompt}
        ]

        if history:
            messages.extend(history)

        messages.append({"role": "user", "content": message})

        # Up to 6 rounds of tool calling
        for _ in range(10):
            response = client.chat.completions.create(
            model="gpt-oss-120b",
                messages=messages,
                tools=TOOLS,
                max_tokens=500,
                temperature=0.7,
            )

            choice = response.choices[0]

            # If the model wants to call tools
            if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
                messages.append(choice.message)

                for tool_call in choice.message.tool_calls:
                    fn_name = tool_call.function.name
                    fn = TOOL_MAP.get(fn_name)
                    if fn:
                        try:
                            # Parse JSON arguments from the model
                            raw_args = tool_call.function.arguments
                            kwargs = json.loads(raw_args) if raw_args else {}
                            kwargs['currency'] = currency
                            
                            # Call the function with db, uid, and the provided arguments
                            result = await fn(db, uid, **kwargs)
                        except Exception as te:
                            result = f"Error in {fn_name}: {str(te)}"
                    else:
                        result = f"Unknown tool: {fn_name}"

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    })
                continue

            # Model returned a final text response
            return choice.message.content or "I couldn't generate a response. Please try again."

        return "Sorry! Please try again in a moment."
    except Exception:
        return "I'm sorry, I encountered an internal error while processing your request."
