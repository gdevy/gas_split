from datetime import datetime
from typing import Optional, List, Union
from uuid import UUID

from bson import ObjectId
from pydantic import BaseModel


class Participant(BaseModel):
    name: str
    access_token: str

    email: str


class Passenger(Participant):
    paid_status: bool = False
    confirmed_status: bool = False


class Driver(Participant):
    pass


class Receipt(BaseModel):
    image: bytes
    submitted_date: datetime
    approved: bool


class Trip(BaseModel):
    id: UUID
    trip_name: str

    driver: Driver
    passengers: List[Passenger]
    receipts: Union[List[Receipt], List[ObjectId]]

    class Config:
        arbitrary_types_allowed = True

