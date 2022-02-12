
from urllib.parse import quote_plus
from mongomantic import BaseRepository
from mongomantic import connect as connect_mongo
from mongomantic.core.errors import WriteError
from mongomantic.core.mongo_model import MongoDBModel
from mongomantic.core.base_repository import Index
from typing import List, Type


from app.config import settings
from app.models.notion import NotionTask
from app.models.google import GoogleTask

# Setup MongoDB connection
mongo_uri = f"mongodb://{quote_plus(settings.mongo_username)}:{quote_plus(settings.mongo_password)}@{settings.mongo_url}"

connect_mongo(mongo_uri, settings.mongo_db) 

class ExtendedRepository(BaseRepository):

    class Meta:
        @property
        def model(self) -> Type[MongoDBModel]:
            """Model class that subclasses MongoDBModel"""
            raise NotImplementedError

        @property
        def collection(self) -> str:
            """String representing the MongoDB collection to use when storing this model"""
            raise NotImplementedError

        @property
        def indexes(self) -> List[Index]:
            """List of MongoDB indexes that should be setup for this particular model"""
            raise NotImplementedError

    @classmethod
    def update(cls, model):
        """Updates an entry in MongoDB"""
        try:
            document = model.to_mongo()
            res = cls._get_collection().update_one({"_id": model.id}, {"$set": document})
        except Exception as e:
            raise WriteError(f"Error updating document: \n{e}")
        
        if res.modified_count != 1:
            raise WriteError(f"Error updating document: \n")

        document["_id"] = model.id

        return cls.Meta.model.from_mongo(document)


class NotionTaskRepository(ExtendedRepository):

    class Meta:
        model = NotionTask
        collection = "notion-task"


class GoogleTaskRepository(ExtendedRepository):
    
    class Meta:
        model = GoogleTask
        collection = "google-task"
