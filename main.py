import json

import firebase_admin
from firebase_admin import credentials
from flask import Flask, request

from exceptions import TableNotFoundException
from service import set_device_token, add_to_watching_session_service, \
    remove_watching_session_service, get_watching_sessions_service, get_sessions_service, get_current_token_service, \
    start, add_job, stop

app = Flask(__name__)

cred = credentials.Certificate("find-my-ticket-firebase-adminsdk-o9yyr-7974c10b9f.json")
firebase_admin.initialize_app(cred)


@app.post("/")
def index():
    outgoing_station = request.json["outgoing"]
    destination_station = request.json["destination"]
    departure_date = request.json["date"]
    add_job(outgoing_station, destination_station, departure_date)
    start()
    return ""


@app.delete("/")
def delete_job():
    stop()


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
    if type(sessions) == TableNotFoundException:
        return {"data": "", "error": sessions.message}, sessions.code
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


@app.get("/devices")
def get_current_token():
    token = get_current_token_service()
    return {"data": token, "error": ""}


if __name__ == '__main__':
    app.run()
