import json
import pytest
from os import path
from datetime import date, datetime, time, timedelta, timezone

from app.models.notion import NotionTask, NotionTasks, NotionTime, NotionDatabaseModel
from app.tests.fixtures.notion import parent_params, setup_notion_test_tasks
from app.config import settings


def load_notion_json(name: str) -> dict:
    response_path = path.join(path.dirname(__file__), "json_notion", name)
    with open(response_path, "r") as f:
        return json.load(f)


######################### Test the NotionTime model ############################

class TestNotionTime():
    notion_d_str = "2022-02-12"
    notion_dt_str = "2022-02-12T13:00:00+01:00"  # With CET timezone

    def test_date_str(self):
        notion_time = NotionTime.from_notion(self.notion_d_str)
        assert notion_time.to_notion() == self.notion_d_str
        assert notion_time.dt.date() == date(year=2022, month=2, day=12)
        assert notion_time.has_time == False

    def test_datetime_str(self):
        notion_time = NotionTime.from_notion(self.notion_dt_str)
        assert notion_time.to_notion() == self.notion_dt_str
        assert notion_time.dt.date() == date(year=2022, month=2, day=12)
        assert notion_time.has_time
        assert notion_time.dt == datetime.combine(date(year=2022, month=2, day=12), time(hour=13, tzinfo=timezone(timedelta(seconds=3600))))


##################### Test the NotionDatabaseModel model #######################

class TestNotionDatabaseModel:
    def test_get_database(self):
        # Test a general database
        db = NotionDatabaseModel.get(id=settings.notion_task_db)
        assert db.Meta.database_id == settings.notion_task_db
        assert db.title == "Tasks"

        # Invalid db id
        with pytest.raises(RuntimeError):
            NotionDatabaseModel.get("nonexistent-db-id")

    def test_list_tasks_from_database(self, setup_notion_test_tasks):
        # List results from database with no model, should return dict(s)
        db = NotionDatabaseModel.get(id=settings.notion_task_db)
        res = db.list()
        tasks = [t for t in res]
        assert isinstance(tasks[0], dict)
        assert len(tasks) == 2



######################### Test the NotionTasks model ###########################

class TestNotionTasks:
    def test_meta(self):
        task_db = NotionTasks()
        assert task_db.Meta.database_id == settings.notion_task_db
        
    def test_list(self, setup_notion_test_tasks):
        tasks = list(NotionTasks().list())
        assert isinstance(tasks[0], NotionTask)
        assert len(tasks) == 2

    def test_get(self, setup_notion_test_tasks):
        parent, _ = setup_notion_test_tasks
        n_task = NotionTasks.get(parent.notion_id)

        for attrib in parent_params.keys():
            assert getattr(n_task, attrib) == parent_params[attrib]

        # list and get should give the same values
        tasks = list(NotionTasks().list())
        fetched_task = NotionTasks().get(tasks[0].notion_id)
        assert tasks[0].dict() == fetched_task.dict()


######################### Test the NotionTask model ############################

class TestNotionTask:

    def test_from_notion(self):
        notion_response = load_notion_json("notion_task_page_response.json")
        task = NotionTask.from_notion(notion_response)

        assert task.notion_id == notion_response["id"]
        assert task.title == notion_response["properties"]["Task"]["title"][0]["plain_text"]
        assert task.notes == notion_response["properties"]["Notes"]["rich_text"][0]["plain_text"]
        assert task.status.to_notion() == notion_response["properties"]["Status"]["select"]
        assert [l.to_notion() for l in task.labels] == notion_response["properties"]["Labels"]["multi_select"]
        assert task.bucket_id == notion_response["properties"]["Bucket"]["relation"][0]["id"]
        assert task.subtask_ids == [x["id"] for x in notion_response["properties"]["Subtasks"]["relation"]]
        assert task.parent_task_ids == [x["id"] for x in notion_response["properties"]["Parent task"]["relation"]]
        assert task.due.datetime() == datetime(year=2022, month=2, day=12, hour=13, tzinfo=timezone(timedelta(seconds=3600)))
        assert task.updated.datetime() == datetime(year=2022, month=2, day=4, hour=19, minute=1)
        assert task.database_id == notion_response["parent"]["database_id"]

    def test_to_notion(self):
        notion_response = load_notion_json("notion_task_page_response.json")
        task = NotionTask.from_notion(notion_response)
        correct_kwargs = load_notion_json("notion_task_short.json")

        kwargs = task.to_notion_kwargs()
        for field in correct_kwargs.keys():
            assert kwargs[field] == correct_kwargs[field]

    def test_create_and_remove_task_in_notion(self):
        synced_time = datetime.now()
        task = NotionTask(
            **parent_params,
            synced=synced_time
        )
        saved_task = task.notion_save()

        assert saved_task.notion_id
        assert saved_task.updated

        for field in ["title", "notes", "status", "labels", "bucket_id", "subtask_ids", "parent_task_ids", "due", "database_id", "synced"]:
            assert saved_task.__getattribute__(field) == task.__getattribute__(field)

        saved_task.notion_delete()

    def test_update_task_in_notion(self):
        task = NotionTask(title="New test task", database_id=settings.notion_task_db)

        task = task.notion_save()
        assert task.notion_id
        assert task.title == "New test task"
        assert task.notes == None

        task.title = "More amazing title 🎉"
        task.notes = "Task notes"
        task.due = NotionTime(dt=datetime(year=2022, month=2, day=1), has_time=False)
        task = task.notion_save()
        assert task.title == "More amazing title 🎉"
        assert task.notes == "Task notes"
        assert task.due.datetime() == datetime(year=2022, month=2, day=1)

        task.notion_delete()

