import pytest
from backend.schemas.split import SplitRequest, SplitType
from backend.services.splitting.calculator import SplitCalculator

calculator = SplitCalculator()

def test_equal_split():
    request = SplitRequest(split_type=SplitType.EQUAL, users=["Alice", "Bob", "Charlie"])
    shares = calculator.calculate_split(100.0, request)
    assert len(shares) == 3
    # 100 / 3 = 33.33, remainder goes to first user -> 33.34
    assert shares[0]["share_amount"] == 33.34
    assert shares[1]["share_amount"] == 33.33
    assert shares[2]["share_amount"] == 33.33

def test_custom_split():
    request = SplitRequest(
        split_type=SplitType.CUSTOM, 
        users=["Alice", "Bob"], 
        custom_shares={"Alice": 60.0, "Bob": 40.0}
    )
    shares = calculator.calculate_split(100.0, request)
    assert shares[0]["share_amount"] == 60.0
    assert shares[1]["share_amount"] == 40.0

def test_proportional_split():
    request = SplitRequest(
        split_type=SplitType.PROPORTIONAL,
        users=["Alice", "Bob", "Charlie"],
        custom_shares={"Alice": 2, "Bob": 1, "Charlie": 1} # Weights: 50%, 25%, 25%
    )
    shares = calculator.calculate_split(100.0, request)
    assert shares[0]["share_amount"] == 50.0
    assert shares[1]["share_amount"] == 25.0
    assert shares[2]["share_amount"] == 25.0

def test_item_based_split_with_tax():
    # Items total $40, but Bill is $50 (so $10 tax/tip distributed proportionally)
    items = [
        {"id": 1, "description": "Burger", "amount": 15.0},
        {"id": 2, "description": "Salad", "amount": 10.0},
        {"id": 3, "description": "Drinks", "amount": 15.0}
    ]
    request = SplitRequest(
        split_type=SplitType.ITEM_BASED,
        users=["Alice", "Bob", "Charlie"],
        item_assignments={
            1: ["Alice"],           # Alice owes 15
            2: ["Bob"],             # Bob owes 10
            3: ["Alice", "Charlie"] # Alice 7.5, Charlie 7.5
        }
    )
    # Subtotals before tax: Alice=22.5, Bob=10, Charlie=7.5
    # Total assigned = 40.
    # Tax = 10. Proportions: Alice = 22.5/40 = 0.5625 * 10 = 5.625 -> 5.63
    # Bob = 10/40 = 0.25 * 10 = 2.50
    # Charlie = 7.5/40 = 0.1875 * 10 = 1.875 -> 1.88
    # Total Tax Assigned = 5.63 + 2.50 + 1.88 = 10.01. Diff = -0.01 given to Alice.
    # New Tax: Alice = 5.62, Bob = 2.50, Charlie = 1.88. Sum = 10.0.
    
    shares = calculator.calculate_split(50.0, request, items)
    
    assert sum(s["share_amount"] for s in shares) == 50.0
    # Alice: 22.5 + 5.62 = 28.12
    # Bob: 10 + 2.50 = 12.50
    # Charlie: 7.5 + 1.88 = 9.38
    # Sum = 28.12 + 12.50 + 9.38 = 50.0
    for s in shares:
        if s["user_name"] == "Alice":
            assert s["share_amount"] == 28.12
        elif s["user_name"] == "Bob":
            assert s["share_amount"] == 12.50
        elif s["user_name"] == "Charlie":
            assert s["share_amount"] == 9.38
