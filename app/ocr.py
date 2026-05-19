# ============================================================================
# OCR Service — Tesseract + Cerebras LLM for receipt parsing
# Ported from ocr_backend, adapted for our async PostgreSQL app
# ============================================================================
from __future__ import annotations

import cv2
import numpy as np
import pytesseract
from PIL import Image
import time
import json
import re
import os
from typing import Dict, Any, Tuple, List

from cerebras.cloud.sdk import Cerebras
from app.config import settings

# Configure Tesseract path if set
_tesseract_cmd = settings.tesseract_cmd or os.getenv("TESSERACT_CMD")
if _tesseract_cmd:
    pytesseract.pytesseract.tesseract_cmd = _tesseract_cmd


# ---------------------------------------------------------------------------
# Image Preprocessing + OCR Text Extraction
# ---------------------------------------------------------------------------
class OCRProcessor:
    """Handles image preprocessing and Tesseract text extraction."""

    def preprocess_image(self, image_bytes: bytes) -> np.ndarray:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Failed to decode image.")
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        return gray

    def extract_text(self, image_bytes: bytes) -> Tuple[str, dict]:
        start_time = time.time()
        try:
            processed_img = self.preprocess_image(image_bytes)
            pil_img = Image.fromarray(processed_img)
            custom_config = r'--oem 3 --psm 4'
            text = pytesseract.image_to_string(pil_img, config=custom_config)
            processing_time = time.time() - start_time
            metrics = {
                "processing_time": processing_time,
                "confidence": 85.0,
            }
            return text, metrics
        except Exception as e:
            raise RuntimeError(f"OCR Processing failed: {str(e)}")


# ---------------------------------------------------------------------------
# Cerebras LLM Parser  (replaces Groq)
# ---------------------------------------------------------------------------
class CerebrasReceiptParser:
    """Uses Cerebras LLM to parse raw OCR text into structured receipt data."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.cerebras_api_key or os.getenv("CEREBRAS_API_KEY", "")
        self.client = Cerebras(api_key=self.api_key) if self.api_key else None

    def is_available(self) -> bool:
        return self.client is not None and bool(self.api_key)

    def parse_text(self, text: str) -> Dict[str, Any]:
        if not self.is_available():
            raise ValueError("Cerebras API key is not configured.")

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
        Return ONLY the JSON, no extra text.

        CRITICAL INSTRUCTIONS:
        1. For EVERY line item, extract its Description and the Total Amount for that line.
        2. The sum of all item amounts + cgst + sgst + additional_charge should generally equal total_amount.
        3. If you cannot extract certain fields, use sensible defaults (0.0 for numbers, "Unknown" for strings).

        Schema:
        {json.dumps(schema, indent=2)}

        Receipt OCR Text:
        {text}
        """

        response = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a precise receipt parsing AI. Always output valid JSON."},
                {"role": "user", "content": prompt}
            ],
            model="gpt-oss-120b",
            temperature=0.0,
        )

        try:
            content = response.choices[0].message.content.strip()

            # Clean markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:].strip()
                content = content.strip()

            parsed = json.loads(content)

            # Validate and clean items
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

            # Clean numeric fields
            for field in ['total_amount', 'cgst', 'sgst', 'additional_charge']:
                try:
                    parsed[field] = float(parsed.get(field, 0.0))
                except (ValueError, TypeError):
                    parsed[field] = 0.0

            # Fail-safe total check
            cgst = parsed.get('cgst', 0.0)
            sgst = parsed.get('sgst', 0.0)
            add_charge = parsed.get('additional_charge', 0.0)
            total_amt = parsed.get('total_amount', 0.0)
            calculated_grand = calculated_subtotal + cgst + sgst + add_charge

            if abs(calculated_grand - total_amt) > 5.0 and abs(calculated_subtotal - total_amt) > 5.0:
                if total_amt == 0.0 or total_amt < calculated_subtotal:
                    parsed['total_amount'] = calculated_grand

            return parsed
        except Exception as e:
            raise RuntimeError(f"Failed to parse LLM response: {str(e)}")


# ---------------------------------------------------------------------------
# Regex fallback parser (no LLM needed)
# ---------------------------------------------------------------------------
class RegexReceiptParser:
    """Fallback parser using regex when LLM is unavailable."""

    def __init__(self):
        self.date_pattern = re.compile(r'\b(\d{1,4}[-./]\d{1,2}[-./]\d{1,4})\b')
        self.amount_pattern = re.compile(
            r'\b(?:total|amount due|balance|sum)\s*[:$]?\s*(\d+[.,]\d{2})\b', re.IGNORECASE
        )
        self.item_pattern = re.compile(r'^(.+?)\s+(\d+[.,]\d{2})$')

    def parse_text(self, text: str) -> Dict[str, Any]:
        from datetime import datetime
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        # Merchant
        merchant = "Unknown Merchant"
        for line in lines[:3]:
            if not self.date_pattern.search(line) and not self.amount_pattern.search(line):
                merchant = line.title()
                break

        # Date
        date_str = datetime.utcnow().strftime('%d/%m/%Y')
        match = self.date_pattern.search(text)
        if match:
            date_str = match.group(1).replace('-', '/').replace('.', '/')

        # Total
        total = 0.0
        match = self.amount_pattern.search(text)
        if match:
            try:
                total = float(match.group(1).replace(',', '.'))
            except ValueError:
                pass

        # Items
        items = []
        for line in lines:
            lower_line = line.lower()
            if any(kw in lower_line for kw in ['total', 'tax', 'balance', 'change', 'cash', 'visa', 'mastercard']):
                continue
            m = self.item_pattern.search(line)
            if m:
                desc = m.group(1).strip()
                try:
                    amt = float(m.group(2).replace(',', '.'))
                    if amt > 0:
                        items.append({"description": desc, "amount": amt})
                except ValueError:
                    continue

        if not total and items:
            total = sum(i['amount'] for i in items)

        return {
            "merchant": merchant,
            "date": date_str,
            "total_amount": total,
            "cgst": 0.0,
            "sgst": 0.0,
            "additional_charge": 0.0,
            "items": items,
        }


# ---------------------------------------------------------------------------
# Combined high-level function used by the endpoint
# ---------------------------------------------------------------------------
def process_receipt(image_bytes: bytes, api_key: str | None = None) -> Dict[str, Any]:
    """
    Process a receipt image:
      1. OCR extraction via Tesseract
      2. Structured parsing via Cerebras LLM (or regex fallback)
    Returns dict with items, totals, taxes, etc.
    """
    processor = OCRProcessor()
    raw_text, metrics = processor.extract_text(image_bytes)

    # Try LLM parser first
    llm_parser = CerebrasReceiptParser(api_key)
    if llm_parser.is_available():
        parsed = llm_parser.parse_text(raw_text)
    else:
        parsed = RegexReceiptParser().parse_text(raw_text)

    parsed['raw_text'] = raw_text
    parsed['processing_time'] = metrics['processing_time']
    parsed['confidence'] = metrics['confidence']
    return parsed
