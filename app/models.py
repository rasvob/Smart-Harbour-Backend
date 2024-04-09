from datetime import datetime
from enum import Enum
from sqlmodel import Field, SQLModel, Relationship
from typing import Optional

class RoleEnum(str, Enum):
    admin = "admin"
    regular = "regular"

class BoatLengthEnum(str, Enum):
    pod_8m = "pod 8m"
    nad_8m = "nad 8m"

class PaymentStatusEnum(str, Enum):
    zaplaceno = "Zaplaceno"
    nezaplaceno = "Nezaplaceno"
    neplati = "Neplatí"

class StateOfBoatEnum(str, Enum):
    kotvi = "Kotví"
    prujezd = "Průjezd"

class UserBase(SQLModel):
    full_name: str
    username: str
    email: str | None = None
    role: RoleEnum = RoleEnum.regular
    is_active: bool = True

class UserCreate(UserBase):
    password: str

class User(UserBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    hashed_password: str

class StateBase(SQLModel):
    arrival_time: datetime | None = None
    departure_time: datetime | None = None
    best_detected_identifier: str | None = None
    best_detected_boat_length: BoatLengthEnum | None = None
    payment_status: PaymentStatusEnum = PaymentStatusEnum.nezaplaceno
    time_in_marina: int | None = None
    state_of_boat : StateOfBoatEnum = StateOfBoatEnum.prujezd
    added_manually: bool = False
    weird_state: bool = False
    edit_timestamp: datetime | None = None

class State(StateBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    first_boat_pass_id: int | None = Field(default=None, foreign_key="boatpass.id")
    last_boat_pass_id: int | None = Field(default=None)
    # first_boat_pass = Relationship(sa_relationship_kwargs={ 'foreign_keys': [first_boat_pass_id] })
    # last_boat_pass = Relationship(sa_relationship_kwargs={ 'foreign_keys': [last_boat_pass_id] })
    boat_passes: list["BoatPass"] = Relationship(back_populates="state", sa_relationship_kwargs={ 'foreign_keys': "[State.first_boat_pass_id]" })

class BoatPassBase(SQLModel):
    camera_id: int
    timestamp: datetime
    image_filename: str
    raw_text: str | None = None
    detected_identifier: str | None = None
    boat_length: BoatLengthEnum | None = None

class BoatPass(BoatPassBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    state: State | None = Relationship(back_populates="boat_passes")
    bounding_boxes: list["BoundingBox"] = Relationship(back_populates="boat_pass")

class BoundingBoxBase(SQLModel):
    left: float
    top: float
    right: float
    bottom: float
    confidence: float
    class_identifier: int

class BoundingBox(BoundingBoxBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    boat_pass_id: int = Field(foreign_key="boatpass.id")
    boat_pass: BoatPass = Relationship(back_populates="bounding_boxes")
    ocr_results: list["OcrResult"] = Relationship(back_populates="bounding_box")

class OcrResultBase(SQLModel):
    left: float
    top: float
    right: float
    bottom: float
    text: str
    confidence: float

class OcrResult(OcrResultBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    bounding_box_id: int = Field(foreign_key="boundingbox.id")
    bounding_box: BoundingBox = Relationship(back_populates="ocr_results")