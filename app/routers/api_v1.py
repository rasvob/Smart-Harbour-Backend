import os
import io
import logging
import base64
from fastapi import FastAPI, HTTPException, APIRouter, Request, Depends
from sqlmodel import Session, select
from app.core.app_logger import AppLogger
from app.core.app_config import app_config
from app.core.db import engine, Hero
from app.routers.deps import SessionDep

logger = AppLogger(__name__, logging._nameToLevel[app_config.LOG_LEVEL]).get_logger()
api_v1_router = APIRouter(
    prefix=app_config.API_V1_STR,
    tags=["api"],
    responses={404: {"description": "Not found"}},
)

@api_v1_router.get("/test")
async def test():
    logger.info("test")
    logger.debug("test DDDD")
    return {"Status": "OK"}

@api_v1_router.put("/write")
async def write(session: SessionDep):
    hero_1 = Hero(name="Deadpond", secret_name="Dive Wilson")
    hero_2 = Hero(name="Spider-Boy", secret_name="Pedro Parqueador")
    hero_3 = Hero(name="Rusty-Man", secret_name="Tommy Sharp", age=48)

    session.add(hero_1)
    session.add(hero_2)
    session.add(hero_3)
    session.commit()
    return {"Status": "OK"}

@api_v1_router.get("/heros")
async def heros(session: SessionDep):
    statement = select(Hero)
    heros = session.exec(statement).all()
    logger.debug(heros)
    return heros

@api_v1_router.get("/hero/{hero_name}")
async def heros(hero_name:str, session: SessionDep):
    statement = select(Hero).where(Hero.name == hero_name)
    hero = session.exec(statement).first()
    logger.debug(hero)
    return hero