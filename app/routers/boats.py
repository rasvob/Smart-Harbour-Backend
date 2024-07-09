import os
import io
import logging
import base64
from typing import Any, List
from fastapi import FastAPI, HTTPException, APIRouter, Request, Depends
from sqlmodel import Session, select
from app.core.app_logger import AppLogger
from app.core.app_config import app_config
from app.models import OcrResult, State, StateBase, User, BoatPass, BoatPassCreate, BoatPassPublic, OcrResultPublic, PaymentStatusEnum, BoatLengthEnum, StateOfBoatEnum, ImagePayload
from app import crud
from app.routers.deps import SessionDep, TokenDep, CurrentUser, get_current_active_user

logger = AppLogger(__name__, logging._nameToLevel[app_config.LOG_LEVEL]).get_logger()
boat_router = APIRouter(
    prefix=app_config.API_V1_STR,
    tags=["api"],
    responses={404: {"description": "Not found"}},
)

@boat_router.get("/boat-passes", dependencies=[Depends(get_current_active_user)], response_model=list[BoatPassPublic])
async def read_boat_passes(session: SessionDep) -> list[BoatPassPublic]:
    res_db = crud.get_all_boat_passes(session=session)
    return res_db

@boat_router.post("/boat-pass",dependencies=[Depends(get_current_active_user)], response_model=BoatPassPublic)
async def create_boat_pass(session: SessionDep, boat_pass: BoatPassCreate, image_data: ImagePayload) -> BoatPassPublic:
    res = crud.create_boat_pass(session=session, boat_pass=boat_pass)
    image_path = os.path.join(app_config.DATA_FOLDER, res.image_filename)
    try:
        # logger.debug(f"Saving image: {image_data.image}")
        img_data = base64.b64decode(image_data.image)
        with open(image_path, "wb") as new_file:
            new_file.write(img_data)
    except Exception as e:
        logger.error(f"Error while saving image: {e}")
        logger.error(f"Image data: {image_data.image[:20]}, ..., {image_data.image[-20:]}")
    return res

# TODO: Just for debugging purposes, remove this endpoint
@boat_router.post("/boat-pass-state", response_model=BoatPassPublic)
async def create_boat_pass_state(session: SessionDep, boat_pass: BoatPassCreate) -> BoatPassPublic:
    boat_pass_res = crud.create_boat_pass(session=session, boat_pass=boat_pass)
    logger.debug(f"Created pass: {boat_pass_res}")
    state = StateBase(arrival_time=boat_pass_res.timestamp, 
                      departure_time=boat_pass_res.timestamp, 
                      best_detected_identifier=boat_pass_res.detected_identifier, 
                      best_detected_boat_length=boat_pass_res.boat_length, 
                      payment_status=PaymentStatusEnum.nezaplaceno, 
                      time_in_marina=15, 
                      state_of_boat=StateOfBoatEnum.prujezd)
    crud.create_state(session=session, state=state, first_boat_pass_id=boat_pass_res.id, last_boat_pass_id=None)
    logger.debug(f"Created state: {state}")
    
    return boat_pass_res

@boat_router.post('/state', dependencies=[Depends(get_current_active_user)], response_model=State)
async def create_state(session: SessionDep, state: StateBase) -> State:
    return crud.create_state(session=session, state=state)

@boat_router.get("/ocr-results", dependencies=[Depends(get_current_active_user)], response_model=list[OcrResult])
async def ocr_results(session: SessionDep) -> list[OcrResult]:
    return crud.get_all_ocr_results(session=session)

@boat_router.get("/states", dependencies=[Depends(get_current_active_user)], response_model=list[State])
async def get_all_states(session: SessionDep) -> list[State]:
    return crud.get_states(session=session)