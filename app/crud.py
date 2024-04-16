from app.models import User, UserCreate, DbInitState
from app.core.security import get_password_hash, verify_password
from sqlmodel import Session, select

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