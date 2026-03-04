from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from backend.database.session import get_db
from backend.schemas.expense import ExpenseCreate, ExpenseResponse, OCRMetricsBase, LineItemUpdate, ExpenseUpdate
from backend.schemas.split import SplitRequest, UserShareResponse
from backend.repositories.expense_repo import ExpenseRepository
from backend.repositories.metrics_repo import MetricsRepository
from backend.services.ocr.processor import OCRProcessor
from backend.services.ocr.parser import OCRParser
from backend.services.ocr.llm_parser import LLMParser
from backend.services.expense.categoriser import ExpenseCategoriser
from backend.services.splitting.calculator import SplitCalculator

router = APIRouter()

ocr_processor = OCRProcessor()
ocr_parser = OCRParser()
llm_parser = LLMParser()
categoriser = ExpenseCategoriser()
split_calc = SplitCalculator()

@router.post("/upload", response_model=ExpenseResponse)
async def upload_receipt(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")

    image_bytes = await file.read()
    
    # 1. OCR Extraction
    try:
        raw_text, ocr_metrics = ocr_processor.extract_text(image_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR Processing failed: {str(e)}")
        
    # 2. Parsing into structured data
    if llm_parser.is_available():
        parsed_data = llm_parser.parse_text(raw_text)
    else:
        parsed_data = ocr_parser.parse_text(raw_text)
    
    # 3. Categorisation
    category = categoriser.categorise(raw_text, parsed_data["merchant"])
    parsed_data["category"] = category
    parsed_data["confidence"] = ocr_metrics["confidence"]
    
    # 4. Save to Database
    repo = ExpenseRepository(db)
    expense_create = ExpenseCreate(**parsed_data)
    
    db_expense = repo.create(expense_create)
    
    # 5. Save Metrics
    metrics_repo = MetricsRepository(db)
    metrics_base = OCRMetricsBase(**ocr_metrics)
    metrics_repo.save_metrics(db_expense.id, metrics_base)
    
    return db_expense

@router.get("/", response_model=List[ExpenseResponse])
def get_expenses(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    repo = ExpenseRepository(db)
    return repo.get_all(skip=skip, limit=limit)

@router.get("/{expense_id}", response_model=ExpenseResponse)
def get_expense(expense_id: int, db: Session = Depends(get_db)):
    repo = ExpenseRepository(db)
    expense = repo.get_by_id(expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense

@router.post("/{expense_id}/split", response_model=List[UserShareResponse])
def split_expense(expense_id: int, request: SplitRequest, db: Session = Depends(get_db)):
    # Verify expense
    repo = ExpenseRepository(db)
    expense = repo.get_by_id(expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
        
    items = []
    if request.split_type == "item_based":
        items = [{"id": item.id, "amount": item.amount} for item in expense.line_items]

    try:
        shares = split_calc.calculate_split(expense.total_amount, request, items)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    repo.save_shares(expense_id, shares)
    
    # fetch updated object user shares to match response
    db.refresh(expense)
    return expense.user_shares
    
@router.post("/{expense_id}/assign-items")
def assign_items(expense_id: int, item_assignments: dict, db: Session = Depends(get_db)):
    """
    item_assignments: Dict mapping line item ID to list of user names
    Example: {"1": ["Alice", "Bob"], "2": ["Charlie"]}
    """
    repo = ExpenseRepository(db)
    expense = repo.get_by_id(expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
        
    repo.save_line_item_assignments(expense_id, item_assignments)
    return {"message": "Items assigned successfully"}

@router.put("/{expense_id}/items", response_model=ExpenseResponse)
def update_expense_items(expense_id: int, items: List[LineItemUpdate], db: Session = Depends(get_db)):
    repo = ExpenseRepository(db)
    expense = repo.get_by_id(expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
        
    items_data = [{"id": item.id, "description": item.description, "amount": item.amount} for item in items]
    repo.update_line_items(expense_id, items_data)
    
    # Refresh to return updated items
    db.refresh(expense)
    return expense

@router.put("/{expense_id}", response_model=ExpenseResponse)
def update_expense_details(expense_id: int, expense_update: ExpenseUpdate, db: Session = Depends(get_db)):
    repo = ExpenseRepository(db)
    expense = repo.get_by_id(expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
        
    updated_expense = repo.update_core_details(expense_id, expense_update.model_dump())
    return updated_expense

@router.delete("/{expense_id}", response_model=dict)
def delete_expense(expense_id: int, db: Session = Depends(get_db)):
    repo = ExpenseRepository(db)
    success = repo.delete(expense_id)
    if not success:
        raise HTTPException(status_code=404, detail="Expense not found")
    return {"message": "Expense deleted successfully"}
