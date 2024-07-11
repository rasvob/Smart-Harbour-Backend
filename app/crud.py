from datetime import datetime, timedelta, tzinfo, UTC
from typing import List

from sqlalchemy import func, column
from app.models import PaymentStatusEnum, StateUpdate, User, UserCreate, DbInitState, BoatPass, BoatPassBase, BoundingBox, BoundingBoxBase, OcrResult, OcrResultBase, BoatPassCreate, State, StateBase, DashboardData
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

def get_states(*, session: Session) -> List[State]:
    statement = select(State).order_by(State.id.desc())
    session_states = session.exec(statement).all()
    return session_states

def create_state(*, session: Session, state: StateBase, first_boat_pass_id: int | None = None, last_boat_pass_id: int | None = None) -> State:
    state_db = State.model_validate(state, update={"first_boat_pass_id": first_boat_pass_id, "last_boat_pass_id": last_boat_pass_id})
    session.add(state_db)
    session.commit()
    session.refresh(state_db)
    return state_db

def get_state_by_id(*, session: Session, state_id: int) -> State | None:
    statement = select(State).where(State.id == state_id)
    session_state = session.exec(statement).first()
    return session_state

def update_state_payment(*, session: Session, update_state: StateUpdate) -> State:
    state = get_state_by_id(session=session, state_id=update_state.id)
    state.payment_status = update_state.payment_status
    session.add(state)
    session.commit()
    session.refresh(state)
    return state

def update_state_best_detected_identifier(*, session: Session, update_state: StateUpdate) -> State:
    state = get_state_by_id(session=session, state_id=update_state.id)
    state.best_detected_identifier = update_state.best_detected_identifier
    session.add(state)
    session.commit()
    session.refresh(state)
    return state

def update_state_raw(*, session: Session, original_state: State, updated_state: State) -> State:
    state_data = updated_state.model_dump(exclude_unset=True)
    original_state.sqlmodel_update(state_data)
    session.add(original_state)
    session.commit()
    session.refresh(original_state)
    return original_state

def update_state(*, session: Session, updated_state: State) -> State:
    original_state = get_state_by_id(session=session, state_id=updated_state.id)
    return update_state_raw(session=session, original_state=original_state, updated_state=updated_state)

def get_dashboard_data(*, session: Session) -> DashboardData:
    statement_today_arrived = select(func.count(State.id)).where(State.arrival_time + timedelta(days=1) > datetime.now(UTC))
    count_of_today_arrived = session.exec(statement_today_arrived).one()
    statement_today_arrived_undetected_identifier = select(func.count(State.id)).where(State.arrival_time + timedelta(days=1) > datetime.now(UTC)).where(column("best_detected_identifier").contains('?'))
    count_of_today_arrived_undetected_identifier = session.exec(statement_today_arrived_undetected_identifier).one()

    statement_today_departed = select(func.count(State.id)).where(State.departure_time + timedelta(days=1) > datetime.now(UTC))
    count_of_today_departed = session.exec(statement_today_departed).one()
    statement_today_departed_undetected_identifier= select(func.count(State.id)).where(State.departure_time + timedelta(days=1) > datetime.now(UTC)).where(column("best_detected_identifier").contains('?'))
    count_of_today_departed_undetected_identifier = session.exec(statement_today_departed_undetected_identifier).one()

    statement_today_in_marina = select(func.count(State.id)).where(State.arrival_time + timedelta(days=1) > datetime.now(UTC)).where(State.departure_time == None)
    count_of_today_in_marina = session.exec(statement_today_in_marina).one()
    statement_today_in_marina_undetected_identifier= select(func.count(State.id)).where(State.arrival_time + timedelta(days=1) > datetime.now(UTC)).where(State.departure_time == None).where(column("best_detected_identifier").contains('?'))
    count_of_today_in_marina_undetected_identifier = session.exec(statement_today_in_marina_undetected_identifier).one()

    statement_today_payed = select(func.count(State.id)).where(State.arrival_time + timedelta(days=1) > datetime.now(UTC)).where(State.payment_status == PaymentStatusEnum.zaplaceno)
    count_of_today_payed = session.exec(statement_today_payed).one()

    statement_today_nonpayed = select(func.count(State.id)).where(State.arrival_time + timedelta(days=1) > datetime.now(UTC)).where(State.payment_status == PaymentStatusEnum.nezaplaceno)
    count_of_today_nonpayed = session.exec(statement_today_nonpayed).one()
    return DashboardData(
        today_arrived=count_of_today_arrived, 
        today_departed=count_of_today_departed, 
        today_in_marina=count_of_today_in_marina, 
        today_payed=count_of_today_payed, 
        today_not_payed=count_of_today_nonpayed,
        today_arrived_undetected_identifier=count_of_today_arrived_undetected_identifier,
        today_departed_undetected_identifier=count_of_today_departed_undetected_identifier,
        today_in_marina_undetected_identifier=count_of_today_in_marina_undetected_identifier
        )

    
