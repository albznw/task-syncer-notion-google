import pytest
from app.models.notion import NotionLabel, NotionStatus, NotionTask, NotionTime, NotionTaskDB, NotionDatabaseModel
from datetime import date, datetime, time, timedelta, timezone
from app.config import settings

def test_NotionTime():
    notion_d_str = "2022-02-12"
    notion_dt_str = "2022-02-12T13:00:00+01:00"  # With CET timezone

    notion_time = NotionTime.from_notion(notion_d_str)
    assert notion_time.to_notion() == notion_d_str
    assert notion_time.dt.date() == date(year=2022, month=2, day=12)
    assert notion_time.has_time == False

    notion_time = NotionTime.from_notion(notion_dt_str)
    assert notion_time.to_notion() == notion_dt_str
    assert notion_time.dt.date() == date(year=2022, month=2, day=12)
    assert notion_time.has_time

    assert notion_time.dt == datetime.combine(date(year=2022, month=2, day=12), time(hour=13, tzinfo=timezone(timedelta(seconds=3600))))


# These tests are made to test Notion -> Python

def test_NotionDatabaseModel():
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

def test_NotionTaskDB():
    task_db = NotionTaskDB()
    assert task_db.Meta.database_id == settings.notion_task_db

    res = task_db.list()
    tasks = [t for t in res]
    assert isinstance(tasks[0], NotionTask)
    assert len(tasks) == 2

def test_NotionTask():
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

    n_task = NotionTaskDB.get("fae45cfe89dd42f7b2c8cffa951eaee3")
    for attrib in test_parent_task_correct.keys():
        assert getattr(n_task, attrib) == test_parent_task_correct[attrib]