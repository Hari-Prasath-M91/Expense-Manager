from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Optional
from backend.models.ocr_metrics import OCRMetrics
from backend.schemas.expense import OCRMetricsBase

class MetricsRepository:
    def __init__(self, session: Session):
        self.session = session

    def save_metrics(self, expense_id: int, metrics: OCRMetricsBase) -> OCRMetrics:
        # Check if exists
        stmt = select(OCRMetrics).where(OCRMetrics.expense_id == expense_id)
        db_metric = self.session.scalars(stmt).first()
        
        if db_metric:
            db_metric.cer = metrics.cer
            db_metric.wer = metrics.wer
            db_metric.processing_time = metrics.processing_time
        else:
            db_metric = OCRMetrics(
                expense_id=expense_id,
                cer=metrics.cer,
                wer=metrics.wer,
                processing_time=metrics.processing_time
            )
            self.session.add(db_metric)
            
        self.session.commit()
        self.session.refresh(db_metric)
        return db_metric
        
    def get_metrics(self, expense_id: int) -> Optional[OCRMetrics]:
        stmt = select(OCRMetrics).where(OCRMetrics.expense_id == expense_id)
        return self.session.scalars(stmt).first()
