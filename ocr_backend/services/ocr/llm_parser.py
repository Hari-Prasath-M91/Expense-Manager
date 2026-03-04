import json
from typing import Dict, Any
from groq import Groq
from backend.core.config import settings

class LLMParser:
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.client = Groq(api_key=self.api_key) if self.api_key else None

    def is_available(self) -> bool:
        return self.client is not None

    def parse_text(self, text: str) -> Dict[str, Any]:
        if not self.is_available():
            raise ValueError("Groq API key is not configured.")

        schema = {
            "merchant": "string",
            "date": "DD/MM/YYYY",
            "total_amount": "float",
            "cgst": "float (or 0.0 if not found)",
            "sgst": "float (or 0.0 if not found)",
            "additional_charge": "float (tips, service charges, packing fees, etc. 0.0 if not found)",
            "items": [
                {
                    "description": "string",
                    "amount": "float"
                }
            ]
        }

        prompt = f"""
        Extract the following information from the OCR receipt text. 
        You MUST respond ONLY with a valid JSON object matching the exact keys and types as the schema below.
        Wait for no further instructions, return only the JSON.

        CRITICAL FAIL-SAFE MATH INSTRUCTIONS:
        1. For EVERY line item, you must extract its Description and the Total Amount for that line.
        2. Check the Grand Total: the sum of all `amount` + `cgst` + `sgst` + `additional_charge` should generally equal `total_amount`.

        Schema:
        {json.dumps(schema, indent=2)}

        Receipt OCR Text:
        {text}
        """

        response = self.client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise receipt parsing AI. Always output valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model="llama-3.1-8b-instant",
            temperature=0.0,
            response_format={"type": "json_object"}
        )

        try:
            content = response.choices[0].message.content
            parsed = json.loads(content)
            
            # Additional cleanup & Fail-Safes
            if 'items' not in parsed or not isinstance(parsed['items'], list):
                parsed['items'] = []
                
            validated_items = []
            calculated_subtotal = 0.0
            
            for item in parsed['items']:
                try:
                    total_item_price = float(item.get('amount', 0.0))
                    
                    item['amount'] = total_item_price
                    validated_items.append(item)
                    calculated_subtotal += total_item_price
                except (ValueError, TypeError):
                    continue
            
            parsed['items'] = validated_items
            
            # Ensuring total_amount is a float
            total_amt = 0.0
            try:
                total_amt = float(parsed.get('total_amount', 0.0))
                parsed['total_amount'] = total_amt
            except (ValueError, TypeError):
                parsed['total_amount'] = 0.0
                
            cgst_amt = 0.0
            try:
                cgst_amt = float(parsed.get('cgst', 0.0))
                parsed['cgst'] = cgst_amt
            except (ValueError, TypeError):
                parsed['cgst'] = 0.0
                
            sgst_amt = 0.0
            try:
                sgst_amt = float(parsed.get('sgst', 0.0))
                parsed['sgst'] = sgst_amt
            except (ValueError, TypeError):
                parsed['sgst'] = 0.0
                
            add_charge_amt = 0.0
            try:
                add_charge_amt = float(parsed.get('additional_charge', 0.0))
                parsed['additional_charge'] = add_charge_amt
            except (ValueError, TypeError):
                parsed['additional_charge'] = 0.0
                
            # Fail-Safe 2: Total Amount Check
            calculated_grand_total = calculated_subtotal + cgst_amt + sgst_amt + add_charge_amt
            # If the extracted total is wildly off (by more than 5 rupees diff from either subtotal or grand total),
            # we favor our mathematical calculation.
            if abs(calculated_grand_total - total_amt) > 5.0 and abs(calculated_subtotal - total_amt) > 5.0:
                print(f"FAIL-SAFE TRIGGERED: Extracted Total ({total_amt}) does not match Items({calculated_subtotal}) + Taxes({cgst_amt}+{sgst_amt}) + Extras({add_charge_amt})")
                if total_amt == 0.0 or total_amt < calculated_subtotal:
                    parsed['total_amount'] = calculated_grand_total
                
            return parsed
        except Exception as e:
            raise RuntimeError(f"Failed to parse LLM response: {str(e)}")
