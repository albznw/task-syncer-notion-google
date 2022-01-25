
from datetime import datetime
from typing import List
from pydantic import BaseModel

from notion_client import Client
from app.config import settings

client = Client(auth=settings.notion_secret)

NOTION_BUCKET_ID = ""

class NotionBucket(BaseModel):
    id: str
    name: str | None = None

    @classmethod
    def get(cls, id: str):
        page = client.pages.retrieve(id)
        params = {
            "id": id,
            "name": page["properties"]["Name"]["title"][0]["plain_text"]
        }
        return cls(**params)


class NotionStatus(BaseModel):
    id: str
    name: str
    color: str


class NotionLabel(NotionStatus):
    pass


class NotionSubtask(BaseModel):
    id: str
    task: str
    status: NotionStatus | None = None
    labels: List[NotionLabel] = []
    details: str | None = None
    due: datetime | None = None

class NotionTask(BaseModel):
    id: str
    task: str
    status: NotionStatus | None = None
    labels: List[NotionLabel] = []
    bucket: NotionBucket | None = None
    subtasks: List[NotionSubtask] = []
    details: str | None = None
    due: datetime | None = None

    @classmethod
    def from_notion(cls, notion_task_page: dict):
        
        bucket = None
        if tmp:= notion_task_page["properties"]["Bucket"]["relation"]:
            bucket = NotionBucket.get(tmp[0]["id"])

        details = None
        if tmp:= notion_task_page["properties"]["Details"]["rich_text"]:
            details = tmp[0]["plain_text"]

        due = None
        if tmp:= notion_task_page["properties"]["Due"]["date"]:
            due = datetime.strptime(tmp["start"], "%Y-%m-%d")
        
        params = {
            "id": notion_task_page["id"],
            "task": notion_task_page["properties"]["Task"]["title"][0]["plain_text"],
            "status": notion_task_page["properties"]["Status"]["select"],
            "labels": notion_task_page["properties"]["Labels"]["multi_select"],
            "bucket": bucket,
            "details": details,
            "due": due,
        }

        return cls(**params)
