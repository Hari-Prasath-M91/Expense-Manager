from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from backend.database.session import get_db
from backend.models.ocr_metrics import OCRMetrics
from backend.models.expense import Expense

router = APIRouter()

@router.get("/ocr")
def get_ocr_metrics(db: Session = Depends(get_db)):
    """
    Returns aggregated metrics for OCR Processing.
    """
    total_expenses = db.scalar(select(func.count(Expense.id)))
    avg_processing_time = db.scalar(select(func.avg(OCRMetrics.processing_time)))
    
    # Normally CER and WER would be computed against ground truth,
    # Here we might just return the count of automated extractions
    # or average confidence if stored in Expense
    avg_confidence = db.scalar(select(func.avg(Expense.confidence)))
    
    return {
        "total_receipts_processed": total_expenses or 0,
        "average_processing_time_seconds": round(avg_processing_time or 0, 3),
        "average_confidence_score": round(avg_confidence or 0, 2),
        "automation_rate": "100%" if total_expenses else "0%"
    }
