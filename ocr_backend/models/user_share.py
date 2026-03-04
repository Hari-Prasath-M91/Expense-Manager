from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from backend.database.session import Base

class UserShare(Base):
    __tablename__ = "user_shares"

    id = Column(Integer, primary_key=True, index=True)
    expense_id = Column(Integer, ForeignKey("expenses.id", ondelete="CASCADE"), nullable=False)
    user_name = Column(String, index=True)
    share_amount = Column(Float)

    expense = relationship("Expense", back_populates="user_shares")
