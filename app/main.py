import logging
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

logger = AppLogger(__name__, logging._nameToLevel[app_config.LOG_LEVEL]).get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.debug('Starting app')
    yield
    logger.debug('Shuting down app')

init_db(app_config.INIT_DB)

app = FastAPI()

origins = [
    "http://localhost",
    "https://localhost",
    "http://localhost:4000",
    "https://localhost:4000",
    "https://smartharbour.vsb.cz",
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
                except HTTPException as e:
                    await websocket.send_json({'type': 'error', 'message': str(e.detail)})
                    raise WebSocketDisconnect()
    except WebSocketDisconnect:
        manager.disconnect(websocket)