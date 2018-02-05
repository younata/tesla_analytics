from typing import List

from bson import ObjectId
from pymongo import MongoClient


class StorageService(object):
    def __init__(self, uri):
        self.client = MongoClient(uri)
        self.db = self.client["tesla"]

    def store(self, collection: str, data: dict) -> ObjectId:
        return self.db[collection].insert_one(data)

    def retrieve(self, collection: str, **kwargs) -> List[dict]:
        return self.db[collection].find(kwargs)
