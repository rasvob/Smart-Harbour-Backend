import os
import io
import logging
import base64
from fastapi import FastAPI, HTTPException, APIRouter, Request, Depends
from sqlmodel import Session, select
from app.core.app_logger import AppLogger
from app.core.app_config import app_config
from app.models import User
from app.routers.deps import SessionDep

logger = AppLogger(__name__, logging._nameToLevel[app_config.LOG_LEVEL]).get_logger()
boat_router = APIRouter(
    prefix=app_config.API_V1_STR,
    tags=["api"],
    responses={404: {"description": "Not found"}},
)

@boat_router.get("/users", response_model=list[User])
async def users(session: SessionDep) -> list[User]:
    statement = select(User)
    users = session.exec(statement).all()
    logger.debug(users)
    return users