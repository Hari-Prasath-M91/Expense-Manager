import logging
from sqlalchemy import text
from backend.database.session import engine, Base
from backend.models import Expense, LineItem, UserShare, OCRMetrics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    
    # Create SQLite FTS5 table and triggers for Expenses
    with engine.connect() as conn:
        # Create FTS5 virtual table
        conn.execute(text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS expense_fts USING fts5(
                merchant, 
                category, 
                content='expenses', 
                content_rowid='id'
            );
        """))
        
        # Triggers to keep FTS table in sync with expenses table
        # Insert trigger
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS expense_ai AFTER INSERT ON expenses BEGIN
                INSERT INTO expense_fts(rowid, merchant, category) 
                VALUES (new.id, new.merchant, new.category);
            END;
        """))
        
        # Delete trigger
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS expense_ad AFTER DELETE ON expenses BEGIN
                INSERT INTO expense_fts(expense_fts, rowid, merchant, category) 
                VALUES ('delete', old.id, old.merchant, old.category);
            END;
        """))
        
        # Update trigger
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS expense_au AFTER UPDATE ON expenses BEGIN
                INSERT INTO expense_fts(expense_fts, rowid, merchant, category) 
                VALUES ('delete', old.id, old.merchant, old.category);
                INSERT INTO expense_fts(rowid, merchant, category) 
                VALUES (new.id, new.merchant, new.category);
            END;
        """))
        conn.commit()
    logger.info("Database initialized with FTS5.")

if __name__ == "__main__":
    init_db()
