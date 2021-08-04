import base64
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from uuid import uuid4, UUID
import secrets

from bson import ObjectId
from pydantic import BaseModel
from pymongo import ReturnDocument

from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import HTMLResponse
from fastapi.requests import Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse, Response

from models.trip import Trip, Driver, Passenger, Receipt
from mongo_interface import db_client

store = Path(r'/Users/gregdevyatov/Projects/gas_split/store')

app = FastAPI()
app.mount("/static1", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="static/templates")


@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/receipt/{receipt_id}")
async def get_image(receipt_id: str):
    receipt = db_client['receipts'].find_one(
        {'_id': ObjectId(base64.urlsafe_b64decode(receipt_id))}
    )

    return Response(receipt['image'], media_type="image/png")


@app.post("/submit_receipt/{trip_id}")
async def submit_receipt(trip_id: str, access_token: str = None, file: UploadFile = File(...)):
    trip = db_client['trips'].find_one(
        {'id': UUID(bytes=base64.urlsafe_b64decode(trip_id)), }
    )

    print('trip', trip)
    trip = Trip(**trip)

    new_receipt = Receipt(
        image=await file.read(),
        submitted_date=datetime.now(),
        approved=trip.driver.access_token == access_token
    )

    new_receipt_id = db_client['receipts'].insert_one(new_receipt.dict())

    result = db_client['trips'].find_one_and_update(
        filter={
            'id': trip.id,
        },
        update={
            "$push": {'receipts': new_receipt_id.inserted_id, }
        },
        return_document=ReturnDocument.AFTER
    )
    print(result)
    return RedirectResponse(url=f"/trip/{trip_id}?access_token={access_token}", status_code=303)


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
        'access_token': secrets.token_urlsafe(8)
    }

    friends = [{
        'name': form_fields[f'friends[{_}][name]'],
        'email': form_fields[f'friends[{_}][email]'],
        'access_token': secrets.token_urlsafe(8)
    } for _ in range(5)]

    new_id = uuid4()

    new_trip = Trip(
        id=new_id,
        trip_name=trip_name,
        driver=Driver(**driver),
        passengers=[Passenger(**friend) for friend in friends if friend['name']],
        receipts=[],
    )

    db_client['trips'].insert_one(new_trip.dict())

    shortened_uuid = base64.urlsafe_b64encode(bytes.fromhex(new_id.hex)).decode()
    return RedirectResponse(url=f"/trip/{shortened_uuid}?access_token={driver['access_token']}", status_code=303)


@app.get("/trip/{trip_id}", response_class=HTMLResponse)
def read_items(request: Request, trip_id: str, access_token: str):
    trip = db_client['trips'].find_one({'id': UUID(bytes=base64.urlsafe_b64decode(trip_id))})

    receipts = list(db_client['receipts'].find(
        filter={
            '_id': {'$in': trip['receipts']},
            'approved': True,
        },
    ))
    trip = Trip(
        **{**trip,
           'receipts': receipts,
           }
    )
    driver = trip.driver.access_token == access_token

    # db_id = trip.pop('_id')
    return templates.TemplateResponse(
        "trip.html",
        {
            "request": request,
            'trip_name': trip.trip_name,
            'trip_id': trip_id,
            'driver': driver,
            'access_token': access_token,
            'participants': [p.dict() for p in trip.passengers],
            'receipts': [base64.urlsafe_b64encode(receipt['_id'].binary).decode() for receipt in receipts]
        })
