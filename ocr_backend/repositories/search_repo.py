from sqlalchemy.orm import Session
from sqlalchemy import text, select
from typing import List, Tuple
from backend.models.expense import Expense
from backend.schemas.search import SearchRequest

class SearchRepository:
    def __init__(self, session: Session):
        self.session = session

    def search_expenses(self, req: SearchRequest) -> Tuple[List[Expense], int]:
        filters = []
        params = {}
        
        if req.query:
            filters.append("""(
                e.id IN (SELECT rowid FROM expense_fts WHERE expense_fts MATCH :fts_query)
                OR e.merchant LIKE :like_query
                OR e.category LIKE :like_query
                OR e.id IN (SELECT expense_id FROM line_items WHERE description LIKE :like_query)
            )""")
            # Append wildcard for prefix match in FTS5
            params["fts_query"] = f"{req.query}*"
            params["like_query"] = f"%{req.query}%"
            
        if req.merchant:
            filters.append("e.merchant LIKE :merchant")
            params["merchant"] = f"%{req.merchant}%"
            
        if req.category:
            filters.append("e.category = :category")
            params["category"] = req.category
            
        if req.min_amount is not None:
            filters.append("e.total_amount >= :min_amount")
            params["min_amount"] = req.min_amount
            
        if req.max_amount is not None:
            filters.append("e.total_amount <= :max_amount")
            params["max_amount"] = req.max_amount
            
        if req.date_from:
            filters.append("e.date >= :date_from")
            params["date_from"] = req.date_from
            
        if req.date_to:
            filters.append("e.date <= :date_to")
            params["date_to"] = req.date_to
            
        where_clause = " AND ".join(filters)
        if where_clause:
            where_clause = f"WHERE {where_clause}"
            
        query_str = f"SELECT e.* FROM expenses e {where_clause} ORDER BY e.created_at DESC"
        
        # Get elements
        stmt = text(query_str)
        result = self.session.execute(stmt, params).fetchall()
        
        # Map back to ORM objects for schemas
        # Note: In a larger app we wouldn't fetchall like this for performance, but it's fine for our scope
        expense_ids = [row[0] for row in result]
        if not expense_ids:
            return [], 0
            
        orm_stmt = select(Expense).where(Expense.id.in_(expense_ids)).order_by(Expense.created_at.desc())
        expenses = list(self.session.scalars(orm_stmt).all())
        
        return expenses, len(expenses)
