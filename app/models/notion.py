from typing import List, Type
from mongomantic import MongoDBModel
from notion_client import Client as NotionClient
from notion_client.errors import APIResponseError
from datetime import date, time, datetime

from app.config import settings

# Setup Notion connection
notion_client = NotionClient(auth=settings.notion_secret)
notion_tasks_db_id = settings.notion_task_db


class NotionBaseModel(MongoDBModel):

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def from_notion(cls):
        raise NotImplementedError

    def to_notion(self):
        raise NotImplementedError

    @classmethod
    def notion_to_kwargs(cls, response: dict) -> dict:
        raise NotImplementedError

    @classmethod
    def from_notion(cls, response: dict):
        """Creates an instance from a Notion task response"""
        return cls(**cls.notion_to_kwargs(response))

    @classmethod
    def from_dict(cls, params: dict):
        """Creates an instance from a dictionary containing NotionTask
        params"""
        return cls(**params)

    def update_from_params(self, params: dict):
        """Takes a set of params that will override the current fields in a new
        instance of this class.

        Note this function does not update Notion nor does it update the mongo
        db.

        Returns:
            [NotionBaseModel]: An updated instance of this task
        """
        new_params = self.dict()

        for field in params.keys():
            new_params[field] = params[field]

        return self.from_dict(new_params)


class NotionTagBase(NotionBaseModel):
    notion_id: str
    name: str
    color: str

    class Meta:
        @property
        def notion_field_name(self) -> str:
            raise NotImplementedError
        
        @property
        def notion_field_type(self) -> str:
            raise NotImplementedError

    def __repr__(self) -> str:
        return str(self.dict())

    def __str__(self) -> str:
        return str(self.dict())

    @classmethod
    def list(cls):
        db_resp = notion_client.databases.retrieve(notion_tasks_db_id)
        field_values = []
        for value in db_resp["properties"][cls.Meta.notion_field_name][cls.Meta.notion_field_type]["options"]:
            field_values.append(cls(**value))
        return field_values

    @classmethod
    def from_notion(cls, status: dict | List) -> dict | List:

        def _create_item(item: dict):
            return cls(**{
                "notion_id": item["id"],
                "name": item["name"],
                "color": item["color"]
            })

        if isinstance(status, dict):
            return _create_item(status)

        elif isinstance(status, List):
            items = []
            for item in status:
                items.append(_create_item(item))
            return items

        return None

    def to_notion(self) -> dict:
        new_dict = self.dict()
        new_dict["id"] = new_dict.pop("notion_id")
        return new_dict


class NotionDatabaseModel(NotionBaseModel):
    title: str | None = None

    class Meta:
        @property
        def model(self) -> Type[NotionBaseModel]:
            """Model class that subclasses NotionBaseModel"""
            raise NotImplementedError
        
        @property
        def database_id(self) -> str:
            """The Notion database ID related to this model"""
            raise NotImplementedError

    @classmethod
    def from_notion(cls, response):
        title = response["title"][0]["plain_text"]
        id = response["id"]
        new_instance = cls(title=title)
        new_instance.Meta.database_id = id
        new_instance.Meta.model = None
        return new_instance

    @classmethod
    def get(cls, id):
        try:
            db_res = notion_client.databases.retrieve(id)
        except APIResponseError:
            raise RuntimeError(f"Notion DB with id {id} does not exist")
        return cls.from_notion(db_res)

    def list(self, **kwargs):
        db_res = notion_client.databases.query(self.Meta.database_id, **kwargs)
        while True:
            for task in db_res["results"]:
                try:
                    yield self.Meta.model.from_notion(task)
                except:
                    yield task
            
            if db_res["has_more"]:
                db_res = notion_client.databases.query(
                    self.Meta.database_id,
                    next_cursor=db_res["next_cursor"]
                )
            else:
                break


class NotionStatus(NotionTagBase):

    class Meta:
        notion_field_name = "Status"
        notion_field_type = "select"


class NotionLabel(NotionTagBase):

    class Meta:
        notion_field_name = "Labels"
        notion_field_type = "multi_select"


class NotionTime(NotionBaseModel):
    dt: datetime
    has_time: bool = True

    @classmethod
    def from_date(cls, d:date=None):
        return cls(dt=datetime.combine(date=d, time=time(second=0)), has_time=False)

    @classmethod
    def from_notion(cls, date_str: str):
        if len(tmp := date_str.split("T")) > 1:
            date_str, time_str = tmp
            dt = datetime.combine(
                date.fromisoformat(date_str),
                time.fromisoformat(time_str)
            )
            return cls(dt=dt)
        return cls.from_date(d=date.fromisoformat(date_str))

    def to_notion(self):
        if self.has_time:
            return self.dt.isoformat()
        return self.dt.date().strftime("%Y-%m-%d")

    def __repr__(self):
        return self.dt

    def __str__(self) -> str:
        return self.dt.isoformat()

    def __eq__(self, other) -> bool:
        return self.dt == other.dt and self.has_time == other.has_time

class NotionBucket(NotionBaseModel):
    # Notion fields
    notion_id: str | None = None
    title: str | None = None

    @classmethod
    def notion_to_kwargs(cls, response: dict) -> dict:
        """Converts the response from Notion to a dict that can be passed to a
        NotionBucket as keyword arguments
        """
        params = {
            "notion_id": response["id"],
            "title": response["properties"]["Title"]["title"][0]["plain_text"]
        }

        return params

    @classmethod
    def from_notion(cls, response: dict):
        """Creates a NotionBucket from a Notion bucket response"""
        return cls(**cls.notion_to_kwargs(response))

class NotionTask(NotionBaseModel):
    # Notion Fields
    notion_id: str | None = None
    title: str | None = None
    notes: str | None = None
    status: NotionStatus | None = None
    labels: List[NotionLabel] = []
    bucket_id: str | None = None
    subtask_ids: List[str] = []
    parent_task_ids: List[str] = []
    due: NotionTime | None = None
    updated: NotionTime | None = None

    # Metafields
    database_id: str
    synced: datetime | None = None

    @classmethod
    def from_notion(cls, response):
        bucket_id = None
        if tmp := response["properties"]["Bucket"]["relation"]:
            bucket_id = tmp[0]["id"].replace("-", "")

        notes = None
        if tmp := response["properties"]["Notes"]["rich_text"]:
            notes = tmp[0]["plain_text"]

        due = None
        if tmp := response["properties"]["Due"]["date"]:
            date_str = tmp["start"]
            due = NotionTime.from_notion(date_str)

        subtask_ids = []
        if tmp := response["properties"]["Subtasks"]["relation"]:
            for task_id in tmp:
                subtask_ids.append(task_id["id"].replace("-", ""))

        parent_task_ids = []
        if tmp := response["properties"]["Parent task"]["relation"]:
            for task_id in tmp:
                parent_task_ids.append(task_id["id"].replace("-", ""))

        params = {
            "notion_id": response["id"],
            "title": response["properties"]["Task"]["title"][0]["plain_text"],
            "status": NotionStatus.from_notion(response["properties"]["Status"]["select"]),
            "labels": NotionLabel.from_notion(response["properties"]["Labels"]["multi_select"]),
            "bucket_id": bucket_id,
            "notes": notes,
            "subtask_ids": subtask_ids,
            "parent_task_ids": parent_task_ids,
            "due": due,
            "updated": NotionTime.from_notion(response["last_edited_time"].replace("Z", "")),
            "database_id": response["parent"]["database_id"].replace("-", "")
        }
        
        return cls(**params)

class NotionTaskDB(NotionDatabaseModel):
    class Meta:
        model = NotionTask
        database_id = settings.notion_task_db

    def __init__(self):
        return

    @classmethod
    def get(cls, id: str, **kwargs):
        page_res = notion_client.pages.retrieve(id, **kwargs)
        # Check that it actually comes from the db
class NotionBuckets(NotionDatabaseModel):
    class Meta:
        model = NotionBucket
        database_id = settings.notion_bucket_db

    def __init__(self):
        return

    @classmethod
    def get(cls, id:str=None, **kwargs) -> NotionBucket:
        page_res = notion_client.pages.retrieve(id, **kwargs)
        # Check that it actually comes from the db
        assert page_res["parent"]["database_id"] == cls.Meta.database_id
        return cls.Meta.model.from_notion(page_res)

    def get_by_title(self, title:str) -> NotionBucket:
        """Fetch bucket by title

        Args:
            title (str, optional): [description]. Defaults to None.
        """
        for bucket in self.list():
                if bucket.title == title:
                    return bucket
