from fastapi import APIRouter
from backend.api.endpoints import expenses, search, metrics

api_router = APIRouter()

api_router.include_router(expenses.router, prefix="/expenses", tags=["expenses"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
