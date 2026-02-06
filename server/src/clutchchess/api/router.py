"""Main API router."""

from fastapi import APIRouter

from clutchchess.api.campaign import router as campaign_router
from clutchchess.api.games import router as games_router
from clutchchess.api.leaderboard import router as leaderboard_router
from clutchchess.api.lobbies import router as lobbies_router
from clutchchess.api.replays import router as replays_router
from clutchchess.auth import get_auth_router

api_router = APIRouter()
api_router.include_router(campaign_router)
api_router.include_router(games_router)
api_router.include_router(leaderboard_router)
api_router.include_router(lobbies_router)
api_router.include_router(replays_router)
api_router.include_router(get_auth_router())
