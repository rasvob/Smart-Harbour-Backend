from collections.abc import Generator
from typing import Annotated
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session
from fastapi import Depends, HTTPException, status
from app.core.db import engine
from app.models import User, TokenPayload
from app.core.app_config import app_config
from jose import jwt, JWTError
from pydantic import ValidationError
import logging
from app.core.app_logger import AppLogger

logger = AppLogger(__name__, logging._nameToLevel[app_config.LOG_LEVEL]).get_logger()

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{app_config.API_V1_STR}/login/access-token"
)

def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_db)]
TokenDep = Annotated[str, Depends(oauth2_scheme)]

def get_current_user(session: SessionDep, token: TokenDep) -> User:
    try:
        payload = jwt.decode(token, app_config.JWT_SECRET, algorithms=[app_config.JWT_ALGORITHM])
        token_data = TokenPayload(**payload)
    except (JWTError, ValidationError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Could not validate credentials")
    
    user = session.get(User, token_data.sub)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return user

CurrentUser = Annotated[User, Depends(get_current_user)]