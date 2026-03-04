import pytest
from backend.schemas.search import SearchRequest
from backend.repositories.search_repo import SearchRepository
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.models import Expense, Base
from backend.database.init_db import init_db

# Mock DB setup
engine = create_engine("sqlite:///:memory:")
SessionLocal = sessionmaker(bind=engine)

@pytest.fixture(scope="module")
def db_session():
    Base.metadata.create_all(bind=engine)
    
    # Needs SQLite FTS table setup for in-memory DB testing
    with engine.connect() as conn:
        from sqlalchemy import text
        conn.execute(text("CREATE VIRTUAL TABLE IF NOT EXISTS expense_fts USING fts5(merchant, category, content='expenses', content_rowid='id');"))
        conn.execute(text("CREATE TRIGGER IF NOT EXISTS expense_ai AFTER INSERT ON expenses BEGIN INSERT INTO expense_fts(rowid, merchant, category) VALUES (new.id, new.merchant, new.category); END;"))
        conn.commit()
        
    db = SessionLocal()
    
    # Add dummy data
    ex1 = Expense(merchant="Walmart", category="Shopping", total_amount=150.0)
    ex2 = Expense(merchant="Uber", category="Travel", total_amount=25.0)
    db.add_all([ex1, ex2])
    db.commit()
    
    yield db
    db.close()

def test_search_by_merchant(db_session):
    repo = SearchRepository(db_session)
    req = SearchRequest(merchant="Wal")
    res, count = repo.search_expenses(req)
    assert count == 1
    assert res[0].merchant == "Walmart"

def test_search_by_category(db_session):
    repo = SearchRepository(db_session)
    req = SearchRequest(category="Travel")
    res, count = repo.search_expenses(req)
    assert count == 1
    assert res[0].merchant == "Uber"

def test_search_free_text(db_session):
    repo = SearchRepository(db_session)
    req = SearchRequest(query="Uber")
    res, count = repo.search_expenses(req)
    assert count == 1
    assert res[0].category == "Travel"
