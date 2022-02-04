
from urllib.parse import quote_plus
from mongomantic import BaseRepository
from mongomantic import connect as connect_mongo

from app.config import settings
from app.models.notion import NotionTask

# Setup MongoDB connection
mongo_uri = f"mongodb://{quote_plus(settings.mongo_username)}:{quote_plus(settings.mongo_password)}@{settings.mongo_url}"

connect_mongo(mongo_uri, settings.mongo_db) 


class NotionTaskRepository(BaseRepository):
    class Meta:
        model = NotionTask
        collection = "notion-task"
