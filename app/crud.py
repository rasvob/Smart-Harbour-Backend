from typing import List
from app.models import User, UserCreate, DbInitState, BoatPass, BoatPassBase, BoundingBox, BoundingBoxBase, OcrResult, OcrResultBase, BoatPassCreate
from app.core.security import get_password_hash, verify_password
from app.core.app_logger import AppLogger
from app.core.app_config import app_config
from sqlmodel import Session, select
import logging

logger = AppLogger(__name__, logging._nameToLevel[app_config.LOG_LEVEL]).get_logger()

def get_init_db_state(*, session: Session) -> DbInitState:
    statement = select(DbInitState)
    session_state = session.exec(statement).first()
    return session_state

def set_init_db_state(*, session: Session, state: DbInitState) -> DbInitState:
    session.add(state)
    session.commit()
    session.refresh(state)
    return state

def create_user(*, session: Session, user_create: UserCreate) -> User:
    user = User.model_validate(user_create, update={"hashed_password": get_password_hash(user_create.password)})
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

def get_user_by_email(*, session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    session_user = session.exec(statement).first()
    return session_user

def get_user_by_username(*, session: Session, username: str) -> User | None:
    statement = select(User).where(User.username == username)
    session_user = session.exec(statement).first()
    return session_user

def authenticate(*, session: Session, username: str, password: str) -> User | None:
    user = get_user_by_username(session=session, username=username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def create_boat_pass(*, session: Session, boat_pass: BoatPassCreate) -> BoatPass:
    logger.debug(f"Parameter boat pass: {boat_pass}")
    boat_pass_db = BoatPass.model_validate(boat_pass, update={"bounding_boxes": [], "state": None})
    session.add(boat_pass_db)
    session.commit()
    session.refresh(boat_pass_db)
    logger.debug(f"Created boat pass: {boat_pass_db}")

    for box in boat_pass.bounding_boxes:
        box_db = BoundingBox.model_validate(box, update={"ocr_results": [], "boat_pass_id": boat_pass_db.id})
        session.add(box_db)
        session.commit()
        session.refresh(box_db)

        for ocr in box.ocr_results:
            ocr_db = OcrResult.model_validate(ocr, update={"bounding_box_id": box_db.id})
            session.add(ocr_db)
            session.commit()
            session.refresh(ocr_db)

    session.refresh(boat_pass_db)
    return boat_pass_db

def get_all_boat_passes(*, session: Session) -> List[BoatPass]:
    statement = select(BoatPass)
    session_boat_passes = session.exec(statement).all()
    return session_boat_passes

def get_bounding_boxes_by_boat_pass_id(*, session: Session, boat_pass_id: int) -> List[BoundingBox]:
    statement = select(BoundingBox).where(BoundingBox.boat_pass_id == boat_pass_id)
    session_boxes = session.exec(statement).all()
    return session_boxes

def get_all_ocr_results(*, session: Session) -> List[OcrResult]:
    statement = select(OcrResult)
    session_ocr = session.exec(statement).all()
    return session_ocr

def get_ocr_results_by_bounding_box_id(*, session: Session, bounding_box_id: int) -> List[OcrResult]:
    statement = select(OcrResult).where(OcrResult.bounding_box_id == bounding_box_id)
    session_ocr = session.exec(statement).all()
    return session_ocr