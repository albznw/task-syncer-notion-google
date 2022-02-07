import pytest
from app.models.notion import NotionLabel, NotionStatus, NotionTask, NotionTasks, NotionTime, NotionDatabaseModel
from datetime import date, datetime, time, timedelta, timezone
from app.config import settings


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


# These tests are made to test Notion -> Python
class TestNotionDatabaseModel:
    def test_NotionDatabaseModel(self):
        # Test a general database
        db = NotionDatabaseModel.get(id=settings.notion_task_db)
        assert db.Meta.database_id == settings.notion_task_db
        assert db.title == "Tasks"

        # List results from database with no model
        res = db.list()
        tasks = [t for t in res]
        assert isinstance(tasks[0], dict)
        assert len(tasks) == 2

        # Invalid db id
        with pytest.raises(RuntimeError):
            NotionDatabaseModel.get("nonexistent-db-id")


class TestNotionTasks:
    def test_correct_model(self):
        task_db = NotionTasks()
        assert task_db.Meta.database_id == settings.notion_task_db
        
    def test_list(self):
        tasks = list(NotionTasks().list())
        assert isinstance(tasks[0], NotionTask)
        assert len(tasks) == 2

    def test_get(self):
        test_parent_task_correct = {
            "title": "Test parent task",
            "notes": "Test notes 🎉",
            "status": NotionStatus(id="c062eac1aff74c30b4bb76656a4c5495", name="ToDo", color="red"),
            "due": NotionTime(dt=datetime(year=2022, month=2, day=12, hour=13, tzinfo=timezone(timedelta(seconds=3600)))),
            "labels": [NotionLabel(id="53a0fc9ca1864363a6dc0229aad1ba7d", name="High Effort", color="pink")],
            "bucket_id": "3c7cd227760a4cf5a867c05c68b68c80",
            "subtask_ids": ["403ad2bfd2da447884b81c3bc58c90d8"],
            "database_id": settings.notion_task_db
        }

        n_task = NotionTasks.get("fae45cfe89dd42f7b2c8cffa951eaee3")
        for attrib in test_parent_task_correct.keys():
            assert getattr(n_task, attrib) == test_parent_task_correct[attrib]

        # list and get should give the same values
        tasks = list(NotionTasks().list())
        fetched_task = NotionTasks().get(tasks[0].notion_id)
        assert tasks[0].dict() == fetched_task.dict()
