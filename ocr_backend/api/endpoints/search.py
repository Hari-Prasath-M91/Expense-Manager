from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database.session import get_db
from backend.schemas.search import SearchRequest, SearchResponse
from backend.repositories.search_repo import SearchRepository

router = APIRouter()

@router.post("/", response_model=SearchResponse)
def search_expenses(request: SearchRequest, db: Session = Depends(get_db)):
    repo = SearchRepository(db)
    expenses, count = repo.search_expenses(request)
    return SearchResponse(results=expenses, total_count=count)
