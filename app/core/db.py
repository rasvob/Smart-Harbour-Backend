from sqlmodel import Session, create_engine, select, SQLModel
from app.core.app_config import app_config
from app.models import User, UserCreate, State, BoatPass, BoundingBox, OcrResult
from app.crud import create_user
from app.core.app_logger import AppLogger
import logging
import json

logger = AppLogger(__name__, logging._nameToLevel[app_config.LOG_LEVEL]).get_logger()
engine = create_engine(str(app_config.SQLALCHEMY_DATABASE_URI), echo=True)

def prepare_data(session: Session) -> None:
    with open(app_config.INIT_DB_FILE, "r") as f:
        init_data = json.load(f)
        for user in init_data["users"]:
            user_create = UserCreate(**user)
            create_user(session=session, user_create=user_create)
            logger.debug(f"Created user: {user}")

def init_db(init_data=False) -> None:
    SQLModel.metadata.create_all(engine)
    
    if init_data:
        with Session(engine) as session:
            prepare_data(session)