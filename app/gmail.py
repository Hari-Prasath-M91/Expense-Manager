import httpx
import json
import base64
from datetime import datetime
from cerebras.cloud.sdk import Cerebras

import asyncio

async def fetch_gmail_expenses(access_token: str, api_key: str, existing_ids: list[str] = None):
    """
    Fetch recent emails from Gmail and parse them into expenses.
    Limits search to the last 24 hours and filters out already scanned IDs.
    Returns: (list_of_expenses, list_of_all_scanned_ids)
    """
    if existing_ids is None: existing_ids = []
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # "after" date filter (last 24 hours)
    import time
    after_date = int(time.time()) - (24 * 60 * 60)
    after_str = datetime.fromtimestamp(after_date).strftime("%Y/%m/%d")
    
    # Broaden query to include common bank/payment/upi keywords
    query = f"after:{after_str} (receipt OR order OR invoice OR payment OR bill OR transaction OR spent OR debit OR paid OR upi OR bank OR alert OR credit OR subscription)"
    
    async with httpx.AsyncClient() as client:
        try:
            print(f"🔍 Searching Gmail... Query: {query}")
            search_res = await client.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                headers=headers,
                params={"q": query, "maxResults": 50} 
            )
            print(f"📡 Gmail API Status: {search_res.status_code}")
            if search_res.status_code != 200:
                print(f"❌ Error Detail: {search_res.text}")
                return [], []
        except Exception as e:
            print(f"❌ Gmail Network/API error: {e}")
            return [], []

        all_messages = search_res.json().get("messages", [])
        print(f"📂 Total messages matching search: {len(all_messages)}")
        
        # Only process emails we haven't seen before
        messages = [m for m in all_messages if m['id'] not in existing_ids]
        
        if not messages:
            if not all_messages:
                print(f"📭 No emails found matching the search criteria for today.")
            else:
                print(f"✅ All {len(all_messages)} found emails have already been scanned before.")
            return [], [m['id'] for m in all_messages]

        print(f"📩 Processing {len(messages)} brand new emails...")
        semaphore = asyncio.Semaphore(3)

        async def process_message(msg_meta):
            msg_id = msg_meta['id']
            try:
                msg_res = await client.get(
                    f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}",
                    headers=headers
                )
                if msg_res.status_code != 200:
                    print(f"⚠️ Failed to fetch message {msg_id}: {msg_res.status_code}")
                    return {"msg_id": msg_id, "is_not_expense": True}
                
                msg = msg_res.json()
                headers_list = msg.get("payload", {}).get("headers", [])
                subject = next((h['value'] for h in headers_list if h['name'].lower() == 'subject'), "No Subject")
                sender = next((h['value'] for h in headers_list if h['name'].lower() == 'from'), "Unknown")
                
                payload = msg.get("payload", {})
                snippet = msg.get("snippet", "")
                
                def find_text_part(p):
                    if p.get("mimeType") == "text/plain":
                        return p.get("body", {}).get("data", "")
                    if "parts" in p:
                        for sub in p["parts"]:
                            found = find_text_part(sub)
                            if found: return found
                    return ""

                body_data = find_text_part(payload) or payload.get("body", {}).get("data", "")
                body_text = snippet
                if body_data:
                    try:
                        import base64
                        decoded = base64.urlsafe_b64decode(body_data).decode("utf-8", errors="ignore")
                        if decoded: body_text = decoded
                    except Exception as e:
                         print(f"⚠️ Decode failed for {msg_id}: {e}")

                # AI Analyze
                async with semaphore:
                    context = f"Subject: {subject}\nSnippet: {snippet}\n\nContent: {body_text[:2000]}"
                    data = await _ai_parse_body(context, api_key)
                    if data:
                        print(f"✨ AI Found Expense in: {subject}")
                        data["msg_id"] = msg_id
                        data["sender"] = sender
                        data["subject"] = subject
                        data["body"] = body_text[:1500]
                        return data
                    else:
                        print(f"⏩ AI skipped (Not an expense): {subject[:30]}...")
            except Exception as e:
                print(f"🔥 Critical error processing {msg_id}: {e}")
            return {"msg_id": msg_id, "is_not_expense": True}

        tasks = [process_message(m) for m in messages]
        results = await asyncio.gather(*tasks)
        
        expenses = [r for r in results if r and not r.get("is_not_expense")]
        non_expenses = [r for r in results if r and r.get("is_not_expense")]
        
        if non_expenses:
             print(f"✅ Mark scanned: {len(non_expenses)} non-expense emails.")

        # Return all IDs that we have now "scanned"
        all_now_scanned = [m['id'] for m in messages]
        
        return expenses, all_now_scanned

async def _ai_parse_body(text, api_key):
    """Use Cerebras to extract structured expense data from email text."""
    client = Cerebras(api_key=api_key)
    
    system_prompt = f"""
    You are an expense extraction expert. 
    Analyze the email content and extract purchase details.
    
    Rules:
    1. If the email mentions any form of spending by the user, extract: amount, currency, category, expense_date, description.
    2. Extract the details about the transaction from the email body and map it to any one of the following categories: Food, Transport, Shopping, Bills, Entertainment, Others.
    3. Date format: YYYY-MM-DD.
    4. If not an expense, return exactly "null".
    5. Return ONLY valid JSON.
    6. If any part of the mail uses a different currency other than INR, return its proper currency code. Example: USD, EUR, GBP, JPY, etc.
    7. You must return the proper currency, make sure you dont return INR for any other currency.
    Today's Date: {datetime.now().strftime("%Y-%m-%d")}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-oss-120b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0,
        )
        
        content = response.choices[0].message.content.strip()
        
        # Clean markdown code blocks if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:].strip()
            content = content.strip()

        if not content or content.lower() == "null" or content == "{}":
            return None
            
        data = json.loads(content)
        
        # Robust key extraction (handles whitespace/casing)
        clean_data = {}
        for k, v in data.items():
            key = k.strip().lower()
            if "amount" in key: clean_data["amount"] = v
            elif "currency" in key: clean_data["currency"] = str(v).upper()[:3]
            elif "category" in key: clean_data["category"] = v
            elif "date" in key: clean_data["expense_date"] = v
            elif "description" in key: clean_data["description"] = v

        if not clean_data.get("currency"):
            clean_data["currency"] = "INR"

        if clean_data.get("amount") and clean_data.get("expense_date"):
            # Ensure amount is a number
            try:
                amt_str = str(clean_data["amount"]).replace(",", "").replace("₹", "").strip()
                import re
                nums = re.findall(r"\d+\.?\d*", amt_str)
                if nums:
                    clean_data["amount"] = float(nums[0])
                else:
                    return None
            except:
                return None
            return clean_data
    except Exception as e:
        print(f"AI Extraction Error: {e}")
        return None

    return None
