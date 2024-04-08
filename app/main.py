import logging
from fastapi import FastAPI
from app.core.app_config import app_config
from app.core.app_logger import AppLogger
from app.core.db import init_db, engine
from app.routers.api_v1 import api_v1_router

logger = AppLogger(__name__, logging._nameToLevel[app_config.LOG_LEVEL]).get_logger()

app = FastAPI()
app.include_router(api_v1_router)

init_db()

@app.get("/")
def read_root():
    return {"Message": "REST API is running!"}

@app.get("/health")
def health_check():
    return {"Status": "Healthy"}

@app.get("/settings")
def settings():
    return {"Settings": app_config}