import os
import io
import logging
import base64
from typing import List
from fastapi import FastAPI, HTTPException, APIRouter, Request, Depends
from sqlmodel import Session, select
from app.core.app_logger import AppLogger
from app.core.app_config import app_config
from app.models import OcrResult, User, BoatPass, BoatPassCreate, BoatPassPublic, OcrResultPublic
from app import crud
from app.routers.deps import SessionDep, TokenDep, CurrentUser

logger = AppLogger(__name__, logging._nameToLevel[app_config.LOG_LEVEL]).get_logger()
boat_router = APIRouter(
    prefix=app_config.API_V1_STR,
    tags=["api"],
    responses={404: {"description": "Not found"}},
)

@boat_router.get("/boat-passes", response_model=list[BoatPassPublic])
async def read_boat_passes(session: SessionDep) -> list[BoatPassPublic]:
    res_db = crud.get_all_boat_passes(session=session)
    return res_db

@boat_router.post("/boat-passes", response_model=BoatPass)
async def create_boat_pass(session: SessionDep, boat_pass: BoatPassCreate) -> BoatPass:
    return crud.create_boat_pass(session=session, boat_pass=boat_pass)

@boat_router.get("/ocr-results", response_model=list[OcrResult])
async def create_boat_pass(session: SessionDep) -> list[OcrResult]:
    return crud.get_all_ocr_results(session=session)