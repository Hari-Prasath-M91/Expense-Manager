from sqlalchemy import Column, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship
from backend.database.session import Base

class OCRMetrics(Base):
    __tablename__ = "ocr_metrics"

    id = Column(Integer, primary_key=True, index=True)
    expense_id = Column(Integer, ForeignKey("expenses.id", ondelete="CASCADE"), unique=True, nullable=False)
    cer = Column(Float, nullable=True) # Character Error Rate
    wer = Column(Float, nullable=True) # Word Error Rate
    processing_time = Column(Float) # Time in seconds

    expense = relationship("Expense", back_populates="ocr_metrics")
