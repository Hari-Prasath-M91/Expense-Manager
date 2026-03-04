from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional
from backend.models.expense import Expense
from backend.models.line_item import LineItem
from backend.models.user_share import UserShare
from backend.schemas.expense import ExpenseCreate

class ExpenseRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, expense_create: ExpenseCreate) -> Expense:
        db_expense = Expense(
            merchant=expense_create.merchant,
            date=expense_create.date,
            total_amount=expense_create.total_amount,
            cgst=expense_create.cgst,
            sgst=expense_create.sgst,
            additional_charge=expense_create.additional_charge,
            category=expense_create.category,
            confidence=expense_create.confidence
        )
        self.session.add(db_expense)
        self.session.flush() # To get db_expense.id

        if expense_create.items:
            for item in expense_create.items:
                db_item = LineItem(
                    expense_id=db_expense.id,
                    description=item.get("description"),
                    amount=item.get("amount"),
                    user_assigned=item.get("user_assigned")
                )
                self.session.add(db_item)

        self.session.commit()
        self.session.refresh(db_expense)
        return db_expense

    def get_by_id(self, expense_id: int) -> Optional[Expense]:
        stmt = select(Expense).where(Expense.id == expense_id)
        return self.session.scalars(stmt).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[Expense]:
        stmt = select(Expense).order_by(Expense.created_at.desc()).offset(skip).limit(limit)
        return list(self.session.scalars(stmt).all())

    def update_category(self, expense_id: int, category: str) -> Optional[Expense]:
        expense = self.get_by_id(expense_id)
        if expense:
            expense.category = category
            self.session.commit()
            self.session.refresh(expense)
        return expense

    def save_shares(self, expense_id: int, shares: List[dict]):
        # Clear existing shares for the specific expense
        stmt = select(UserShare).where(UserShare.expense_id == expense_id)
        existing_shares = self.session.scalars(stmt).all()
        for share in existing_shares:
            self.session.delete(share)
            
        for share_data in shares:
            db_share = UserShare(
                expense_id=expense_id,
                user_name=share_data["user_name"],
                share_amount=share_data["share_amount"]
            )
            self.session.add(db_share)
        self.session.commit()
        
    def save_line_item_assignments(self, expense_id: int, item_assignments: dict):
        for item_id, users in item_assignments.items():
            stmt = select(LineItem).where(LineItem.id == item_id, LineItem.expense_id == expense_id)
            item = self.session.scalars(stmt).first()
            if item:
                item.user_assigned = ",".join(users) # Storing as temp comma separated
        self.session.commit()

    def update_line_items(self, expense_id: int, items_data: List[dict]):
        for item_data in items_data:
            stmt = select(LineItem).where(LineItem.id == item_data["id"], LineItem.expense_id == expense_id)
            item = self.session.scalars(stmt).first()
            if item:
                item.description = item_data.get("description", item.description)
                item.amount = item_data.get("amount", item.amount)
        self.session.commit()

    def update_core_details(self, expense_id: int, details: dict) -> Optional[Expense]:
        expense = self.get_by_id(expense_id)
        if expense:
            expense.merchant = details.get("merchant", expense.merchant)
            expense.date = details.get("date", expense.date)
            expense.category = details.get("category", expense.category)
            expense.total_amount = details.get("total_amount", expense.total_amount)
            expense.cgst = details.get("cgst", expense.cgst)
            expense.sgst = details.get("sgst", expense.sgst)
            expense.additional_charge = details.get("additional_charge", expense.additional_charge)
            self.session.commit()
            self.session.refresh(expense)
        return expense

    def delete(self, expense_id: int) -> bool:
        expense = self.get_by_id(expense_id)
        if expense:
            self.session.delete(expense)
            self.session.commit()
            return True
        return False
