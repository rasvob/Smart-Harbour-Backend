import logging
from fastapi import FastAPI
from app.app_log import AppLogger
from app.config import AppConfig
from app.routers import api_v1_router

app_config = AppConfig()
logger = AppLogger(__name__, logging._nameToLevel[app_config.log_level]).get_logger()
app = FastAPI()
app.include_router(api_v1_router)


@app.get("/")
def read_root():
    return {"Message": "REST API is running!"}

@app.get("/health")
def health_check():
    return {"Status": "Healthy"}