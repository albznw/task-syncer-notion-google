from datetime import datetime
from pydantic import BaseModel
from pymongo import MongoClient
from pymongo.collection import Collection
from app.config import settings


client = MongoClient(f"mongodb+srv://{settings.mongo_db_username}:{settings.mongo_db_password}@cluster0.i4oua.mongodb.net/myFirstDatabase?retryWrites=true&w=majority")
db = client.TaskSyncer
task_mapper_collection: Collection = db.get_collection("task_mapper_collection")
bucket_mapper_collection: Collection = db.get_collection("bucket_mapper_collection")


class NotionGoogleMapper(BaseModel):
    notion_id: str
    google_id: str
    

class TasksMapper(NotionGoogleMapper):
    notion_sync: datetime
    google_sync: datetime

    @classmethod
    def get(cls, notion_id:str=None, google_id:str=None):
        filter = {}
        if notion_id:
            filter["notion_id"] = notion_id
        if google_id:
            filter["google_id"] = google_id
        
        res = task_mapper_collection.find_one(filter=filter)
        if res:
            return cls(**res)
        else:
            return None

    @classmethod
    def find(cls, filter:dict={}):
        res = task_mapper_collection.find(filter=filter)
        return [cls(**x) for x in res]

    @classmethod
    def delete_many(cls, filter:dict) -> int:
        res = task_mapper_collection.delete_many(filter)
        return res.deleted_count

    def create(self):
        res = task_mapper_collection.insert_one(self.dict())
        return res

    def update(self):
        res = task_mapper_collection.update_one(
            {
                "notion_id": self.notion_id,
                "google_id": self.google_id},
            {
                "$set": self.dict()
            }
        )
        return res


class ListBucketMapper(NotionGoogleMapper):
    @classmethod
    def get(cls, notion_id:str=None, google_id:str=None):
        filter = {}
        if notion_id:
            filter["notion_id"] = notion_id
        if google_id:
            filter["google_id"] = google_id
        
        res = bucket_mapper_collection.find_one(filter=filter)
        if res:
            return cls(**res)
        else:
            return None
