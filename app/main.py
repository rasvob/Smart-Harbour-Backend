import logging
import os
from app.models import WebsocketImageData
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.app_config import app_config
from app.core.app_logger import AppLogger
from app.core.connection_manager import ConnectionManager
from app.core.db import init_db, engine
from app.routers.boats import boat_router
from app.routers.login import login_router
from app.routers.deps import ConnectionManagerDep, get_current_user, SessionDep, TokenDep
from fastapi.encoders import jsonable_encoder

logger = AppLogger(__name__, logging._nameToLevel[app_config.LOG_LEVEL]).get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.debug('Starting app')
    yield
    logger.debug('Shuting down app')

init_db(app_config.INIT_DB)

# app = FastAPI()

app = FastAPI(docs_url='/api/v1/docs', redoc_url='/api/v1/redoc', openapi_url='/api/v1/openapi.json')

origins = [
    "http://localhost",
    "https://localhost",
    "http://localhost:4000",
    "https://localhost:4000",
    "https://smartharbour.vsb.cz",
    "http://smartharbour.vsb.cz",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(boat_router)
app.include_router(login_router)

@app.get("/")
def read_root():
    return {"Message": "REST API is running!"}

@app.get("/health")
def health_check():
    return {"Status": "Healthy"}

# TODO: Send cached data to the client
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, session: SessionDep, manager: ConnectionManagerDep):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if data['type'] == 'authorization':
                token_d = TokenDep(data['token'])[7:]
                try:
                    user = get_current_user(session=session, token=token_d)
                    for i, x in enumerate([app_config.WS_CAM_PREVIEW_1, app_config.WS_CAM_PREVIEW_2]):
                        img_path = os.path.join(app_config.DATA_FOLDER, x)

                        if not os.path.exists(img_path):
                            continue

                        with open(img_path, "r") as img_file:
                            img_data = img_file.read()
                        await manager.broadcast(jsonable_encoder(WebsocketImageData(camera_id=i+1, image=img_data)))
                except HTTPException as e:
                    await websocket.send_json({'type': 'error', 'message': str(e.detail)})
                    raise WebSocketDisconnect()
    except WebSocketDisconnect:
        manager.disconnect(websocket)