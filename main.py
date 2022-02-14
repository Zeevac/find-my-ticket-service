import firebase_admin
from firebase_admin import credentials
from flask import Flask, request

from service import scrap_ticket_information, set_device_token

app = Flask(__name__)

cred = credentials.Certificate("find-my-ticket-firebase-adminsdk-o9yyr-7974c10b9f.json")
firebase_admin.initialize_app(cred)


@app.post("/")
def index():
    outgoing_station = request.json["outgoing"]
    destination_station = request.json["destination"]
    departure_date = request.json["date"]
    scrap_ticket_information(outgoing_station, destination_station, departure_date)
    return ""


@app.post("/devices")
def set_device():
    new_token = request.json["token"]
    set_device_token(new_token)
    return {"data": "", "error": ""}


app.run()
