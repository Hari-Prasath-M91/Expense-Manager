import pytest
from backend.services.expense.categoriser import ExpenseCategoriser

def test_categorise_food():
    categoriser = ExpenseCategoriser()
    text = "We went out to a restaurant and had some great pizza."
    merchant = "Joe's Pizza"
    assert categoriser.categorise(text, merchant) == "Food"

def test_categorise_travel():
    categoriser = ExpenseCategoriser()
    text = "Ride sharing service receipt."
    merchant = "Uber"
    assert categoriser.categorise(text, merchant) == "Travel"

def test_categorise_utility():
    categoriser = ExpenseCategoriser()
    text = "Monthly bill for electric and gas."
    merchant = "National Grid"
    assert categoriser.categorise(text, merchant) == "Utilities"

def test_categorise_default():
    categoriser = ExpenseCategoriser()
    text = "Unknown items bought."
    merchant = "Random Store"
    assert categoriser.categorise(text, merchant) == "Others"
