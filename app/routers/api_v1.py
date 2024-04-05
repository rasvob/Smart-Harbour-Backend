import os
import io
import logging
import base64
from fastapi import FastAPI, HTTPException, APIRouter, Request, Depends
from app.app_log import AppLogger
from app.config import AppConfig
from contextlib import asynccontextmanager

app_config = AppConfig()
logger = AppLogger(__name__, logging._nameToLevel[app_config.log_level]).get_logger()
api_v1_router = APIRouter(
    prefix="/api/v1",
    tags=["api"],
    responses={404: {"description": "Not found"}},
)

@api_v1_router.get("/test")
async def test():
    logger.info("test")
    logger.debug("test DDDD")
    return {"Status": "OK"}