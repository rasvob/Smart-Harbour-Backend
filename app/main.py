import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.app_config import app_config
from app.core.app_logger import AppLogger
from app.core.db import init_db, engine
from app.routers.boats import boat_router
from app.routers.login import login_router

logger = AppLogger(__name__, logging._nameToLevel[app_config.LOG_LEVEL]).get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.debug('Starting app')
    yield
    logger.debug('Shuting down app')

init_db(app_config.INIT_DB)

app = FastAPI()
app.include_router(boat_router)
app.include_router(login_router)

@app.get("/")
def read_root():
    return {"Message": "REST API is running!"}

@app.get("/health")
def health_check():
    return {"Status": "Healthy"}