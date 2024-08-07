import secrets
from typing import Literal
from pydantic import Field, computed_field, PostgresDsn
from pydantic_settings  import BaseSettings, SettingsConfigDict
from pydantic_core import MultiHostUrl

class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='API_')
    LOG_LEVEL: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'] = "DEBUG"
    API_V1_STR: str = "/api/v1"
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str = ""

    @computed_field
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        return MultiHostUrl.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )
    
    INIT_DB_FILE: str
    INIT_DB: bool = False
    JWT_SECRET: str = secrets.token_urlsafe(32)
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION: int = 20160
    DATA_FOLDER: str
    WS_CAM_PREVIEW_1:str
    WS_CAM_PREVIEW_2:str


app_config = AppConfig()