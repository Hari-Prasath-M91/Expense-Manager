import json
import httpx
from typing import Dict, List, Any
import uuid
from app.database import DatabasePool

async def get_ai_recommendations(db: DatabasePool, user_id: str, api_key: str) -> Dict[str, Any]:
    uid = uuid.UUID(user_id)
    
    # 1. Fetch data for analysis
    # Get all expenses for the last 30 days or so to summarize
    expenses = await db.fetch(
        "SELECT e.amount, c.name as category, e.description, e.expense_date "
        "FROM expenses e JOIN categories c ON e.category_id = c.category_id "
        "WHERE e.user_id = $1 "
        "ORDER BY e.expense_date DESC LIMIT 50",
        uid
    )
    
    # Get budgets
    budgets = await db.fetch(
        "SELECT b.amount, c.name as category "
        "FROM budgets b JOIN categories c ON b.category_id = c.category_id "
        "WHERE b.user_id = $1",
        uid
    )
    
    # Get user preferred currency
    user_row = await db.fetchrow("SELECT preferred_currency FROM users WHERE user_id = $1", uid)
    currency = user_row['preferred_currency'] if user_row else 'INR'

    if not expenses:
        return {
            "healthScore": 0,
            "recommendations": [
                {
                    "type": "health",
                    "title": "Start Tracking",
                    "body": "Add your first few expenses to get personalized AI financial insights!",
                    "action": "Add Expense"
                }
            ]
        }

    # 2. Prepare summary
    by_category = {}
    total_expenses = 0
    recent_txns = []
    
    for exp in expenses:
        amt = float(exp['amount'])
        cat = exp['category']
        total_expenses += amt
        by_category[cat] = by_category.get(cat, 0) + amt
        if len(recent_txns) < 10:
            recent_txns.append({
                "amount": amt,
                "category": cat,
                "description": exp['description'],
                "date": str(exp['expense_date'])
            })

    # For net income, we might not have 'income' table, but let's assume total income is some fixed value or zero if not tracked
    # User schema doesn't seem to have income. Let's just focus on expenses.
    
    prompt = f"""You are a personal finance AI. Analyze this user's financial data and return ONLY valid JSON (no markdown, no extra text).
All amounts are in {currency}.

Spending Summary:
- Total Expenses: {currency} {total_expenses:.2f}
- Spending by category: {json.dumps(by_category)}
- Budgets set: {json.dumps({b['category']: float(b['amount']) for b in budgets})}
- Recent transactions: {json.dumps(recent_txns)}

Return JSON with this exact structure:
{{
  "healthScore": <number 0-100 based on spending vs budgets and general habits>,
  "recommendations": [
    {{ "type": "budget",     "title": "...", "body": "...", "action": "Add Budget" }},
    {{ "type": "alert",      "title": "...", "body": "...", "action": "View Transactions" }},
    {{ "type": "savings",    "title": "...", "body": "...", "action": "Keep Saving" }},
    {{ "type": "allocation", "title": "...", "body": "...", "action": "Update Profile" }},
    {{ "type": "health",     "title": "...", "body": "...", "action": "Add Expense" }}
  ]
}}"""

    # 3. Call Cerebras API
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://api.cerebras.ai/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                json={
                    "model": "gpt-oss-120b", 
                    "max_tokens": 1024,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a financial analysis AI. Always respond with valid JSON only. No explanation, no markdown.",
                        },
                        {
                            "role": "user",
                            "content": prompt,
                        },
                    ],
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                print(f"Cerebras API Error: {response.text}")
                return {"error": "AI Service unreachable"}
                
            data = response.json()
            text = data['choices'][0]['message']['content']
            
            # Clean JSON
            clean = text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean)
            
        except Exception as e:
            print(f"Recommendation Error: {e}")
            return {"error": str(e)}
