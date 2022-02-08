import pytest
from urllib.parse import quote_plus
from datetime import datetime, timedelta, timezone
from pymongo import MongoClient

from app.models.notion import NotionLabel, NotionTask, NotionTime, NotionStatus
from app.config import settings

mongo_uri = f"mongodb://{quote_plus(settings.mongo_username)}:{quote_plus(settings.mongo_password)}@{settings.mongo_url}"

@pytest.fixture()
def mongo_fixture():
    print("setup")
    db_client = MongoClient(mongo_uri)
    yield
    print("teardown")
    db_client.drop_database(settings.mongo_db)

parent_params = {
    "title": "Test parent task",
    "notes": "Test notes 🎉",
    "status": NotionStatus(notion_id="c062eac1-aff7-4c30-b4bb-76656a4c5495", name="ToDo", color="red"),
    "due": NotionTime(dt=datetime(year=2022, month=2, day=12, hour=13, tzinfo=timezone(timedelta(seconds=3600)))),
    "labels": [NotionLabel(notion_id="53a0fc9c-a186-4363-a6dc-0229aad1ba7d", name="High Effort", color="pink")],
    "bucket_id": "3c7cd227-760a-4cf5-a867-c05c68b68c80",
    "database_id": settings.notion_task_db
}

child_params = {
    "title": "Test subtask",
    "notes": "The notes of the subtask",
    "status": NotionStatus(notion_id="c062eac1-aff7-4c30-b4bb-76656a4c5495", name="ToDo", color="red"),
    "labels": [NotionLabel(notion_id="53a0fc9c-a186-4363-a6dc-0229aad1ba7d", name="High Effort", color="pink")],
    "bucket_id": "3c7cd227-760a-4cf5-a867-c05c68b68c80",
    "database_id": settings.notion_task_db
}


@pytest.fixture()
def setup_notion_test_tasks():
    print("Setting up test tasks in Notion")
    parent_task = NotionTask(**parent_params).notion_save()
    child_task = NotionTask(**child_params, parent_task_ids=[parent_task.notion_id]).notion_save()
    yield parent_task, child_task
    child_task.notion_delete()
    parent_task.notion_delete()
    print("Removing test tasks in Notion")