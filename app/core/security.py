from typing import Any
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from app.core.app_config import app_config

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(subject: str | Any) -> str:
    expire = datetime.utcnow() + timedelta(hours=app_config.JWT_EXPIRATION)
    to_encode = {"exp": expire, "sub": str(subject)}
    return jwt.encode(to_encode, key=app_config.JWT_SECRET, algorithm=app_config.JWT_ALGORITHM)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)