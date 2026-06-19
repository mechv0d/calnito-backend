from fastapi import APIRouter

from app.meals.router import router as meals_router
from app.recommendations.router import router as recommendations_router
from app.stats.router import router as stats_router
from app.users.router import router as users_router

api_router = APIRouter()
api_router.include_router(users_router)
api_router.include_router(meals_router)
api_router.include_router(stats_router)
api_router.include_router(recommendations_router)
