import base64
from pathlib import Path
from typing import List, Optional
from uuid import uuid4, UUID

from pydantic import BaseModel
from shortuuid import ShortUUID
import bson

from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import HTMLResponse
from fastapi.requests import Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse, StreamingResponse, FileResponse, Response

from models.trip import Trip, Participant, Driver, Passenger
from mongo_interface import db_client

short_uuid = ShortUUID()

store = Path(r'/Users/gregdevyatov/Projects/gas_split/store')

app = FastAPI()
app.mount("/static1", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="static/templates")


def shorten_uuid(uuid: UUID) -> UUID:
    return short_uuid.decode(short_uuid.encode(uuid)[:8])


@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/images/{image_name}")
async def get_image(image_name: str):
    img = db_client['images'].find_one(
            {'trip_id': UUID(bytes=base64.urlsafe_b64decode(image_name))}
        )['image']
    return Response(img, media_type="image/png")


@app.post("/images/{image_name}")
async def upload_image(image_name: str, file: UploadFile = File(...)):
    db_client['images'].insert_one(
        {
            'trip_id': UUID(bytes=base64.urlsafe_b64decode(image_name)),
            'image': bson.binary.Binary(await file.read())
        })

    return RedirectResponse(url=f"/trip/{image_name}?driver=True", status_code=303)


class NewTripFriend(BaseModel):
    name: Optional[str]
    email: Optional[str]
    sms: Optional[str]


class NewTripForm(BaseModel):
    trip_name: str
    driver_name: str

    friends: List[NewTripFriend]


@app.post("/new_trip/", response_class=RedirectResponse)
async def create_upload_file(request: Request):
    form_fields = dict(await request.form())

    trip_name = form_fields.pop('trip_name')
    driver = {
        'name': form_fields.pop('driver_name'),
        'email': form_fields.pop('driver_email'),
        'sms': form_fields.pop('driver_sms'),
    }

    friends = [{
        'name': form_fields[f'friends[{_}][name]'],
        'sms': form_fields[f'friends[{_}][sms]'],
        'email': form_fields[f'friends[{_}][email]'],
    } for _ in range(5)]

    new_id = uuid4()

    new_trip = Trip(
        id=new_id,
        trip_name=trip_name,
        driver=Driver(**driver),
        passengers=[Passenger(**friend) for friend in friends if friend['name']],
    )

    db_client['trips'].insert_one(new_trip.dict())

    shortened_uuid = base64.urlsafe_b64encode(bytes.fromhex(new_id.hex)).decode()
    return RedirectResponse(url=f"/trip/{shortened_uuid}?driver=True", status_code=303)


@app.get("/trip/{trip_id}", response_class=HTMLResponse)
def read_items(request: Request, trip_id: str, driver: bool = False, name: str = ''):
    trip = db_client['trips'].find_one({'id': UUID(bytes=base64.urlsafe_b64decode(trip_id))})

    receipt = db_client['images'].find_one({'trip_id': UUID(bytes=base64.urlsafe_b64decode(trip_id))}) is not None
    # db_id = trip.pop('_id')
    trip = Trip(**trip)
    return templates.TemplateResponse(
        "trip.html",
        {
            'driver': driver,
            "request": request,
            'trip_name': trip.trip_name,
            'trip_id': trip_id,
            'participants': [p.dict() for p in trip.passengers],
            'receipt': receipt,
        })
