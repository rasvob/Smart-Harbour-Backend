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
    
    ADMIN_PASSWORD: str
    INIT_DB: bool = False

app_config = AppConfig()