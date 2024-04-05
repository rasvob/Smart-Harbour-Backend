from pydantic import Field
from pydantic_settings  import BaseSettings, SettingsConfigDict

class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='API_')
    log_level: str = Field(...)