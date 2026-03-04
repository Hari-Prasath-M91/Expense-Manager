import re
from typing import Dict, Any, List
from datetime import datetime

class OCRParser:
    def __init__(self):
        # Common regex patterns
        self.date_pattern = re.compile(r'\b(\d{1,4}[-./]\d{1,2}[-./]\d{1,4})\b')
        self.amount_pattern = re.compile(r'\b(?:total|amount due|balance|sum)\s*[:$]?\s*(\d+[.,]\d{2})\b', re.IGNORECASE)
        self.item_pattern = re.compile(r'^(.+?)\s+(\d+[.,]\d{2})$') # Simple: Description Amount

    def parse_text(self, text: str) -> Dict[str, Any]:
        lines = text.split('\n')
        lines = [line.strip() for line in lines if line.strip()]

        merchant = self.extract_merchant(lines)
        date = self.extract_date(text)
        total_amount = self.extract_total(text)
        items = self.extract_line_items(lines)
        
        # If regex missed total, sum up items as fallback
        if not total_amount and items:
            total_amount = sum(float(item['amount']) for item in items)
            
        return {
            "merchant": merchant,
            "date": date,
            "total_amount": float(total_amount) if total_amount else 0.0,
            "cgst": 0.0,
            "sgst": 0.0,
            "items": items
        }

    def extract_merchant(self, lines: List[str]) -> str:
        # Typically the first or second non-empty, non-date line is the merchant
        for line in lines[:3]:
            if not self.date_pattern.search(line) and not self.amount_pattern.search(line):
                return line.title()
        return "Unknown Merchant"

    def extract_date(self, text: str) -> str:
        match = self.date_pattern.search(text)
        if match:
            # Normalize to DD/MM/YYYY
            raw_date = match.group(1).replace('-', '/').replace('.', '/')
            try:
                parts = raw_date.split('/')
                if len(parts[0]) == 4:
                    return f"{parts[2]:0>2}/{parts[1]:0>2}/{parts[0]}"
                else:
                    return f"{parts[0]:0>2}/{parts[1]:0>2}/{parts[2]}"
            except:
                return raw_date
        return datetime.utcnow().strftime('%d/%m/%Y')

    def extract_total(self, text: str) -> float:
        match = self.amount_pattern.search(text)
        if match:
            val = match.group(1).replace(',', '.')
            try:
                return float(val)
            except ValueError:
                pass
                
        # Fallback: find the largest float at the end of a line near 'total'
        lower_text = text.lower()
        if 'total' in lower_text:
            lines = lower_text.split('\n')
            for line in lines:
                if 'total' in line:
                    amounts = re.findall(r'\b\d+[.,]\d{2}\b', line)
                    if amounts:
                        return max([float(a.replace(',', '.')) for a in amounts])
        return 0.0

    def extract_line_items(self, lines: List[str]) -> List[Dict[str, Any]]:
        items = []
        for line in lines:
            # Skip lines that look like totals, tax, etc.
            lower_line = line.lower()
            if any(keyword in lower_line for keyword in ['total', 'tax', 'balance', 'change', 'cash', 'visa', 'mastercard']):
                continue
                
            match = self.item_pattern.search(line)
            if match:
                desc = match.group(1).strip()
                amt_str = match.group(2).replace(',', '.')
                try:
                    amt = float(amt_str)
                    if amt > 0:
                        items.append({"description": desc, "amount": amt, "quantity": 1})
                except ValueError:
                    continue
        return items
