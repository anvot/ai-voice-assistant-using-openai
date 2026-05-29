from typing import Optional, Any

import pymongo
import uuid
from datetime import datetime, timedelta

import config

class Database:
    def __init__(self):
        self.client = pymongo.MongoClient(config.mongodb_uri)
        self.db = self.client["ai_voice_assistant"]

        self.client_collection = self.db["client"]
        self.dialog_collection = self.db["dialog"]

    def check_if_client_exists(self, client_username: str, raise_exception: bool = False):
        if self.client_collection.count_documents({"client_username": client_username}) > 0:
            return True
        else:
            if raise_exception:
                raise ValueError(f"client {client_username} does not exist")
            else:
                return False

    def add_new_client(
        self,
        client_username: str = "",
        first_name: str = "",
        last_name: str = "",
    ):
        client_dict = {
            "client_username": client_username,

            "first_name": first_name,
            "last_name": last_name,

            "last_interaction": datetime.now(),
            "first_seen": datetime.now(),

            "current_dialog_id": None
        }

        if not self.check_if_client_exists(client_username):
            self.client_collection.insert_one(client_dict)

    def start_new_dialog(self, client_username: str):
        self.check_if_client_exists(client_username, raise_exception=True)

        dialog_id = str(uuid.uuid4())
        dialog_dict = {
            "dialog_id": dialog_id,
            "client_username": client_username,
            "start_time": datetime.now(),
            "messages": []
        }

        # add new dialog
        self.dialog_collection.insert_one(dialog_dict)

        # update client's current dialog
        self.client_collection.update_one(
            {"client_username": client_username},
            {"$set": {"current_dialog_id": dialog_id}}
        )

        return dialog_id

    def get_client_attribute(self, client_username: str, key: str):
        self.check_if_client_exists(client_username, raise_exception=True)
        client_dict = self.client_collection.find_one({"client_username": client_username})

        if key not in client_dict:
            return None

        return client_dict[key]

    def set_client_attribute(self, client_username: str, key: str, value: Any):
        self.check_if_client_exists(client_username, raise_exception=True)
        self.client_collection.update_one({"client_username": client_username}, {"$set": {key: value}})

    def get_dialog_messages(self, client_username: str, dialog_window: Optional[int] = 0, dialog_id: Optional[str] = None):
        self.check_if_client_exists(client_username, raise_exception=True)

        if dialog_id is None:
            dialog_id = self.get_client_attribute(client_username, "current_dialog_id")

        dialog_dict = self.dialog_collection.find_one({"dialog_id": dialog_id, "client_username": client_username})
        return dialog_dict["messages"][-dialog_window:]

    def set_dialog_messages(self, client_username: str, dialog_messages: list, dialog_id: Optional[str] = None):
        self.check_if_client_exists(client_username, raise_exception=True)

        if dialog_id is None:
            dialog_id = self.get_client_attribute(client_username, "current_dialog_id")

        self.dialog_collection.update_one(
            {"dialog_id": dialog_id, "client_username": client_username},
            {"$set": {"messages": dialog_messages}}
        )
