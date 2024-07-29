import os
import io
import logging
import base64
from typing import Any, List
from fastapi import FastAPI, HTTPException, APIRouter, Request, Depends
from fastapi.encoders import jsonable_encoder
from sqlmodel import Session, select
from app.core.app_logger import AppLogger
from app.core.app_config import app_config
from app.models import DashboardData, ImageModel, OcrResult, State, StateBase, StateUpdate, User, BoatPass, BoatPassCreate, BoatPassPublic, OcrResultPublic, PaymentStatusEnum, BoatLengthEnum, StateOfBoatEnum, ImagePayload, WebsocketImageData
from app import crud
from app.routers.deps import ConnectionManagerDep, SessionDep, TokenDep, CurrentUser, get_current_active_user

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

@boat_router.get("/dashboard", dependencies=[Depends(get_current_active_user)], response_model=DashboardData)
async def dashboard(session: SessionDep) -> DashboardData:
    return crud.get_dashboard_data(session=session)

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
    logger.debug(f"Creating state: {state}")
    return crud.create_state(session=session, state=state)

@boat_router.put('/state', dependencies=[Depends(get_current_active_user)], response_model=State)
async def update_state_full(session: SessionDep, update_stated: StateUpdate) -> State:
    return crud.update_state(session=session, updated_state=update_stated)

@boat_router.patch('/state/payment', dependencies=[Depends(get_current_active_user)], response_model=State)
async def update_state_payment(session: SessionDep, update_state: StateUpdate) -> State:
    return crud.update_state_payment(session=session, update_state=update_state)

@boat_router.patch('/state/identifier', dependencies=[Depends(get_current_active_user)], response_model=State)
async def update_state_best_detected_identifier(session: SessionDep, update_state: StateUpdate) -> State:
    return crud.update_state_best_detected_identifier(session=session, update_state=update_state)

@boat_router.get("/ocr-results", dependencies=[Depends(get_current_active_user)], response_model=list[OcrResult])
async def ocr_results(session: SessionDep) -> list[OcrResult]:
    return crud.get_all_ocr_results(session=session)

@boat_router.get("/states", dependencies=[Depends(get_current_active_user)], response_model=list[State])
async def get_all_states(session: SessionDep) -> list[State]:
    return crud.get_states(session=session)

@boat_router.post("/preview", dependencies=[Depends(get_current_active_user)], response_model=Any)
async def broadcast_preview(image: ImageModel, manager: ConnectionManagerDep) -> Any:
    await manager.broadcast(jsonable_encoder(WebsocketImageData(camera_id=image.camera_id, image=image.image)))
    img_path = os.path.join(app_config.DATA_FOLDER, app_config.WS_CAM_PREVIEW_1 if image.camera_id == 1 else app_config.WS_CAM_PREVIEW_2)
    with open(img_path, "w") as new_file:
        new_file.write(image.image)

    # await manager.broadcast({'data': 'here'})
    return {"status": "ok"}