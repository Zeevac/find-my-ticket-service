import json

import firebase_admin
from firebase_admin import credentials
from flask import Flask, request

from service import scrap_ticket_information, set_device_token, add_to_watching_session_service, \
    remove_watching_session_service, get_watching_sessions_service, get_sessions_service

app = Flask(__name__)

cred = credentials.Certificate("find-my-ticket-firebase-adminsdk-o9yyr-7974c10b9f.json")
firebase_admin.initialize_app(cred)


@app.post("/")
def index():
    outgoing_station = request.json["outgoing"]
    destination_station = request.json["destination"]
    departure_date = request.json["date"]
    watching_session = request.json["watching_session"]
    scrap_ticket_information(outgoing_station, destination_station, departure_date, watching_session)
    return ""


@app.post("/sessions/watching")
def add_watching_session():
    date = request.json["date"]
    time = request.json["time"]
    add_to_watching_session_service(date, time)
    return {"data": "true", "error": ""}


@app.delete("/sessions/watching/<string:date>")
def remove_watching_session(date):
    time = request.args.get("time")
    remove_watching_session_service(date, time)
    return {"data": "true", "error": ""}


@app.post("/sessions")
def get_sessions():
    outgoing_station = request.json["outgoing"]
    destination_station = request.json["destination"]
    departure_date = request.json["date"]
    sessions = get_sessions_service(outgoing_station, destination_station, departure_date)
    print(sessions)
    return {"data": json.dumps(sessions), "error": ""}


@app.get("/sessions/watching")
def get_watching_sessions():
    date = request.args.get("date")
    sessions = get_watching_sessions_service(date)
    return {"data": json.dumps(sessions), "error": ""}


@app.post("/devices")
def set_device():
    new_token = request.json["token"]
    set_device_token(new_token)
    return {"data": "", "error": ""}


app.run()
