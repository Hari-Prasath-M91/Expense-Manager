import json
import httpx
from typing import Dict, List, Any
from datetime import datetime
import uuid
from app.database import DatabasePool

async def get_ai_recommendations(db: DatabasePool, user_id: str, api_key: str, force_refresh: bool = False) -> Dict[str, Any]:
    uid = uuid.UUID(user_id)
    
    # 0. Check Cache (Server-side)
    today = datetime.now().date()
    if not force_refresh:
        try:
            cached = await db.fetchrow(
                "SELECT recommendation_data FROM ai_recommendation_cache "
                "WHERE user_id = $1 AND cache_date = $2",
                uid, today
            )
            if cached:
                # recommendation_data is stored as JSONB, which asyncpg returns as a dict/list if using json module, 
                # but let's be safe and check if it needs parsing
                data = cached['recommendation_data']
                if isinstance(data, str):
                    return json.loads(data)
                return data
        except Exception as e:
            # Table might not exist yet if schema wasn't re-run, just continue
            print(f"Cache check failed: {e}")

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
    {{ 
      "type": "budget|alert|savings|allocation|health",
      "title": "Descriptive Title",
      "body": "Detailed advice based on actual data",
      "action": "<one of: 'Add Budget', 'Add Expense', 'View Transactions'> OR empty string '' if no app action applies"
    }}
  ]
}}

CRITICAL CONSTRAINTS:
1. Provide a mix of actionable advice and general financial behavioral coaching.
2. If an advice corresponds to an app feature, use 'Add Budget', 'Add Expense', or 'View Transactions'.
3. For general behavioral advice or praise (e.g., "Good job staying under budget!"), set "action": "".
4. SAVINGS ARE NOT EXPENSES: Do not suggest adding savings as an expense or category. Savings advice is ONLY informational and must always have an empty "action": "".
5. DO NOT suggest opening bank accounts, external transfers, investments, or debt management. 
6. Use provided spending vs budget data to give concrete advice (e.g. "You spent {currency} 500 more than your Food budget")."""

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
                    "max_tokens": 2048,
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
            # Robustly extract JSON from the response (in case AI adds conversational filler)
            start_idx = text.find('{')
            end_idx = text.rfind('}')
            if start_idx != -1 and end_idx != -1:
                clean = text[start_idx:end_idx+1]
            else:
                clean = text.strip()
            
            def repair_json(j_str: str) -> str:
                # 1. Basic trimming
                j_str = j_str.strip()
                # 2. Balance brackets/braces if truncated
                stack = []
                for char in j_str:
                    if char in '{[': stack.append(char)
                    elif char == '}': 
                        if stack and stack[-1] == '{': stack.pop()
                    elif char == ']':
                        if stack and stack[-1] == '[': stack.pop()
                
                # Close remaining in reverse order
                while stack:
                    opener = stack.pop()
                    j_str += '}' if opener == '{' else ']'
                return j_str

            try:
                result = json.loads(clean)
            except Exception as json_err:
                try:
                    repaired = repair_json(clean)
                    result = json.loads(repaired)
                    print("DEBUG: JSON Repaired successfully")
                except:
                    print(f"DEBUG: JSON Repair failed: {json_err}")
                    print(f"DEBUG: Text that failed: {clean}")
                    raise json_err

            # Ensure structure is valid
            if not isinstance(result, dict):
                result = {"healthScore": 0, "recommendations": []}
            if "recommendations" not in result:
                result["recommendations"] = []
            if "healthScore" not in result:
                result["healthScore"] = 50

            # If AI returned nothing helpful, add a default tip
            if not result["recommendations"]:
                result["recommendations"].append({
                    "type": "health",
                    "title": "Keep Tracking",
                    "body": "Your data looks good! Continue logging your daily expenses to see more detailed trends.",
                    "action": ""
                })

            # 4. Save to Cache
            try:
                await db.execute(
                    "INSERT INTO ai_recommendation_cache (user_id, cache_date, recommendation_data) "
                    "VALUES ($1, $2, $3) "
                    "ON CONFLICT (user_id) DO UPDATE SET "
                    "cache_date = EXCLUDED.cache_date, "
                    "recommendation_data = EXCLUDED.recommendation_data, "
                    "updated_at = NOW()",
                    uid, today, json.dumps(result)
                )
            except Exception as e:
                print(f"Failed to save to cache: {e}")

            return result
            
        except Exception as e:
            print(f"Recommendation Error: {e}")
            return {"error": str(e)}
