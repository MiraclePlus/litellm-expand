from fastapi import APIRouter

from app.api.routes import connectivity, items, login, private, users, utils, scheduler, identity_eval, identity_eval_model, webhook
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(items.router)
api_router.include_router(scheduler.router)
api_router.include_router(identity_eval.router)
api_router.include_router(identity_eval_model.router)
api_router.include_router(connectivity.router)
api_router.include_router(webhook.router)

if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
