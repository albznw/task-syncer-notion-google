
from datetime import datetime, timezone, time, date, timedelta
from typing import List
from pydantic import BaseModel

from notion_client import APIErrorCode, APIResponseError, Client
from app.config import settings

client = Client(auth=settings.notion_secret)

notion_bucket_db_id = settings.notion_bucket_db
notion_tasks_db_id = settings.notion_task_db


class NotionBaseModel(BaseModel):
    class Config:
        arbitrary_types_allowed = True


class NotionTime:
    s_date: date = None
    s_time: time = None
    tzinfo: timezone = None

    def __init__(self, dateandtime: datetime = None, date: date = None, time: time = None, tzinfo: timezone = None):
        if dateandtime:
            self.s_date = dateandtime.date()
            self.s_time = dateandtime.time()
            self.tzinfo = dateandtime.tzinfo
        else:
            self.s_date = date
            self.s_time = time
            if time and tzinfo == None:
                raise Exception("tzinfo cannot be None if time is specified")
            self.tzinfo = tzinfo

    @classmethod
    def from_notion(cls, date_str: str):
        if len(date_str) < 11:
            return cls(date=datetime.strptime(date_str, "%Y-%m-%d"))
        else:
            dateandtime = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%f%z")
            return cls(dateandtime=dateandtime)

    def to_notion(self):
        if self.s_date and self.s_time and self.tzinfo:
            # Format as Notion wants it so we get the correct timezone
            datet = self.datetime()
            return f'{datet.strftime("%Y-%m-%dT%H:%M")}:00.000{datet.strftime("%z")[:3]}:{datet.strftime("%z")[3:]}'
        else:
            return self.datetime().strftime("%Y-%m-%d")

    def datetime(self) -> datetime:
        if self.s_time == None:
            return datetime(
                year=self.s_date.year,
                month=self.s_date.month,
                day=self.s_date.day,
            )
        else:
            return datetime(
                year=self.s_date.year,
                month=self.s_date.month,
                day=self.s_date.day,
                hour=self.s_time.hour,
                minute=self.s_time.minute,
                second=self.s_time.second,
                tzinfo=self.tzinfo
            )


class NotionBucket(NotionBaseModel):
    id: str
    title: str
    updated: NotionTime
    tasks: List[str] = []

    @classmethod
    def from_notion(cls, notion_page: dict):
        params = {
            "id": notion_page["id"],
            "title": notion_page["properties"]["Name"]["title"][0]["plain_text"],
            "updated": NotionTime.from_notion(notion_page["last_edited_time"]),
            "tasks": [task["id"] for task in notion_page["properties"]["Tasks"]["relation"]]
        }
        return cls(**params)

    @classmethod
    def get(cls, id: str):
        page = client.pages.retrieve(id)
        return NotionBucket.from_notion(page)

    @classmethod
    def list(cls):
        db_res = client.databases.query(notion_bucket_db_id)
        buckets = []
        for bucket in db_res["results"]:
            buckets.append(NotionBucket.from_notion(bucket))
        return buckets


class NotionStatus(BaseModel):
    id: str
    name: str
    color: str


class NotionLabel(NotionStatus):
    pass


class NotionStatuses:
    _statuses: List[NotionStatus] = []

    def _get_statuses(self):
        db_resp = client.databases.retrieve(notion_tasks_db_id)
        for status in db_resp["properties"]["Status"]["select"]["options"]:
            self._statuses.append(NotionStatus(**status))

    def statuses(self):
        if self._statuses == []:
            self._get_statuses()
        return self._statuses

    def get(self, status_id: str):
        if self._statuses == []:
            self._get_statuses()
        for status in self._statuses:
            if status.id == status_id:
                return status


class NotionLabels(BaseModel):
    database_id: str
    labels: List[NotionLabel] = []

    @classmethod
    def init(cls, database_id: str):
        notion_labels = cls(database_id=database_id)
        resp = client.databases.retrieve(database_id)
        for label in resp["properties"]["Labels"]["multi_select"]["options"]:
            notion_labels.labels.append(NotionLabel(**label))
        return notion_labels

    def get(self, id: str):
        for label in self.labels:
            if label.id == id:
                return label
        return None


class NotionTask(NotionBaseModel):
    id: str | None = None
    title: str
    status: NotionStatus | None = None
    labels: List[NotionLabel] = []
    bucket: NotionBucket | str | None = None
    subtasks: List[str] = []
    parent_tasks: List[str] = []
    details: str | None = None
    due: NotionTime | None = None
    synced: NotionTime | None = None

    updated: NotionTime | None = None
    database_id: str

    @classmethod
    def from_notion(cls, notion_task_page: dict):

        bucket = None
        if tmp := notion_task_page["properties"]["Bucket"]["relation"]:
            bucket = NotionBucket.get(tmp[0]["id"])

        details = None
        if tmp := notion_task_page["properties"]["Details"]["rich_text"]:
            details = tmp[0]["plain_text"]

        due = None
        if tmp := notion_task_page["properties"]["Due"]["date"]:
            date_str = tmp["start"]
            due = NotionTime.from_notion(date_str)

        synced = None
        if notion_task_page["properties"].get("Synced"):
            if tmp := notion_task_page["properties"]["Synced"]["date"]:
                date_str = tmp["start"]
                synced = NotionTime.from_notion(date_str)

        subtasks = []
        if tmp := notion_task_page["properties"]["Subtasks"]["relation"]:
            for task_id in tmp:
                subtasks.append(task_id["id"])

        parent_tasks = []
        if tmp := notion_task_page["properties"]["Parent task"]["relation"]:
            for task_id in tmp:
                parent_tasks.append(task_id["id"])

        params = {
            "id": notion_task_page["id"],
            "title": notion_task_page["properties"]["Task"]["title"][0]["plain_text"],
            "status": notion_task_page["properties"]["Status"]["select"],
            "labels": notion_task_page["properties"]["Labels"]["multi_select"],
            "bucket": bucket,
            "details": details,
            "subtasks": subtasks,
            "parent_tasks": parent_tasks,
            "due": due,
            "synced": synced,
            "updated": NotionTime.from_notion(notion_task_page["last_edited_time"]),
            "database_id": notion_task_page["parent"]["database_id"]
        }

        return cls(**params)

    @classmethod
    def list(cls):
        db_res = client.databases.query(notion_tasks_db_id)
        tasks = []
        for task in db_res["results"]:
            tasks.append(cls.from_notion(task))
        return tasks


    @classmethod
    def get(cls, id: str):
        page = client.pages.retrieve(id)
        return cls.from_notion(page)

    @classmethod
    def delete(cls, id: str):
        try:
            return client.blocks.delete(id)
        except APIResponseError:
            pass

    @property
    def label_options(self):
        return NotionLabels.init(database_id=self.database_id)

    def _get_bucket_id(self):
        if isinstance(self.bucket, str):
            return self.bucket
        else:
            return self.bucket.id

    def _get_status_dict_or_none(self):
        if self.status:
            return self.status.dict()
        else:
            return None

    def _get_notion_kwargs(self) -> dict:
        kwargs = {
            "properties": {
                "Task": {
                    "title": [{
                        "type": "text",
                        "text": {
                            "content": self.title
                        }
                    }]
                },
                "Bucket": {
                    "relation": [
                        { "id": self._get_bucket_id() }
                    ]
                },
                "Status": {
                    "select": self._get_status_dict_or_none()
                },
                "Labels": {
                    "multi_select": [label.dict() for label in self.labels]
                },
            },
            "parent": {
                "database_id": self.database_id
            }
        }

        content = []
        if self.details:
            content = [{
                "type": "text",
                "text": {
                    "content": self.details
                }
            }]

        due = None
        if self.due:
            due = { "start": self.due.to_notion() }

        parent_tasks = []
        if self.parent_tasks:
            parent_tasks = [{ "id": task_id } for task_id in self.parent_tasks]
        
        kwargs["properties"] = kwargs["properties"] | {
            "Details": {
                "rich_text": content
            },
            "Due": { "date": due },
            "Parent task": {
                "relation": parent_tasks
            }
        }
        
        if self.synced:
            kwargs["properties"] = kwargs["properties"] | {
                "Synced": {
                    "date": {
                        "start": self.synced.to_notion()
                    }
                }
            }
        
        return kwargs

    def create(self):
        res = client.pages.create(**self._get_notion_kwargs())
        return NotionTask.from_notion(res)
    
    def update(self):
        res = client.pages.update(self.id, **self._get_notion_kwargs())
        return NotionTask.from_notion(res)
