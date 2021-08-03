from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel


class Participant(BaseModel):
    name: str

    email: str
    sms: str


class Passenger(Participant):
    paid_status: bool = False
    confirmed_status: bool = False


class Driver(Participant):
    pass


class Trip(BaseModel):
    id: UUID
    trip_name: str

    driver: Driver
    passengers: List[Passenger]
    receipt: Optional[str]
