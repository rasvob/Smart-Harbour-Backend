import os
import io
import logging
import base64
from typing import Annotated, Any
from fastapi import FastAPI, HTTPException, APIRouter, Request, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from app.core.app_logger import AppLogger
from app.core.app_config import app_config
from app.core.security import create_access_token
from app.models import User, Token, UserBase
from app.routers.deps import SessionDep, TokenDep, CurrentUser
import app.crud as crud

logger = AppLogger(__name__, logging._nameToLevel[app_config.LOG_LEVEL]).get_logger()
login_router = APIRouter(
    prefix=app_config.API_V1_STR,
    tags=["login"],
    responses={404: {"description": "Not found"}},
)

@login_router.post("/login/access-token")
async def login_access_token(session: SessionDep, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    user = crud.authenticate(
        session=session, username=form_data.username, password=form_data.password
    )

    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    access_token = create_access_token(user.id)
    return Token(access_token=access_token)

@login_router.post("/login/current-user", response_model=UserBase)
async def current_user(user: CurrentUser) -> UserBase:
    return user
