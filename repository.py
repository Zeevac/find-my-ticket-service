import yaml
from pymongo import MongoClient

config = yaml.safe_load(open("app.yaml"))
mongo_config = config["mongodb"]
username = mongo_config["username"]
password = mongo_config["password"]
url = mongo_config["url"]
db_name = mongo_config["db"]
client = MongoClient(
    f"mongodb+srv://{username}:{password}@{url}/{db_name}?retryWrites=true&w=majority")


class Repository:
    def __init__(self):
        self.sessions = client.get_database("myDB").sessions

    def get(self, date):
        return self.sessions.find_one({"date": date})

    def get_all(self):
        return self.sessions.find()

    def add(self, date, time):
        if self.get(date) is None:
            self.sessions.insert_one({"date": date, "sessions": [time]})
        else:
            self.sessions.update_one({"date": date}, {"$push": {"sessions": time}})

    def update(self, date, watching):
        self.sessions.update_one({"date": date}, {"$set": {"sessions": watching}}, upsert=True)

    def remove(self, date, time=None):
        if time is None:
            self.sessions.delete_one({"date": date})
        else:
            self.sessions.update_one({"date": date}, {"$pull": {"sessions": {"$in": time}}})
