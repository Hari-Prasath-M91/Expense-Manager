from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from backend.database.session import Base

class LineItem(Base):
    __tablename__ = "line_items"

    id = Column(Integer, primary_key=True, index=True)
    expense_id = Column(Integer, ForeignKey("expenses.id", ondelete="CASCADE"), nullable=False)
    description = Column(String)
    amount = Column(Float)
    user_assigned = Column(String, nullable=True) # E.g., user who is assigned this item

    expense = relationship("Expense", back_populates="line_items")
