from sqlmodel import Session, create_engine, select, SQLModel
from app.core.app_config import app_config
from app.models import Hero

engine = create_engine(str(app_config.SQLALCHEMY_DATABASE_URI), echo=True)

def init_db() -> None:
    SQLModel.metadata.create_all(engine)