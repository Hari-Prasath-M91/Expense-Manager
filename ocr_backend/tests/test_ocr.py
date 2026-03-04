import pytest
from backend.services.ocr.parser import OCRParser

parser = OCRParser()

def test_parse_merchant_and_total():
    text = """Walmart Supercenter
03/15/2026
1 Apple 1.99
2 Bananas 1.50
TOTAL 3.49
Visa 1234
    """
    result = parser.parse_text(text)
    
    assert result["merchant"] == "Walmart Supercenter"
    assert "2026" in result["date"] or "03-15-2026" in result["date"]
    assert result["total_amount"] == 3.49
    assert len(result["items"]) == 2
    assert result["items"][0]["amount"] == 1.99
    assert result["items"][0]["description"] == "1 Apple"
    assert result["items"][1]["amount"] == 1.50
    assert result["items"][1]["description"] == "2 Bananas"

def test_parse_fallback_total():
    text = """Joe's Diner
04/01/2026
Burger 12.50
Fries 4.50
"""
    result = parser.parse_text(text)
    # Total missing, fallback is to sum items
    assert result["total_amount"] == 17.0
    assert len(result["items"]) == 2
