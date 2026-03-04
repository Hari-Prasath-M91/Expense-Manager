from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database.session import Base

class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    merchant = Column(String, index=True)
    date = Column(String) # Storing as text
    total_amount = Column(Float)
    cgst = Column(Float, default=0.0)
    sgst = Column(Float, default=0.0)
    additional_charge = Column(Float, default=0.0)
    category = Column(String, index=True)
    confidence = Column(Float) # Overall OCR confidence
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    line_items = relationship("LineItem", back_populates="expense", cascade="all, delete-orphan")
    user_shares = relationship("UserShare", back_populates="expense", cascade="all, delete-orphan")
    ocr_metrics = relationship("OCRMetrics", back_populates="expense", uselist=False, cascade="all, delete-orphan")
