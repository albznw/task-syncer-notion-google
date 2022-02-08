import pytest
from datetime import datetime

from app.models.google import GoogleTask, GoogleStatus
from app.config import settings


dev_tasklist_id = settings.google_default_tasklist


test_task_template = GoogleTask(
    tasklist=dev_tasklist_id,
    title="New task",
    due=datetime(year=2022, month=2, day=6),
    notes="Test notes",
    status=GoogleStatus.todo,
    synced=datetime.now()
)

child_task_template = GoogleTask(
    tasklist=dev_tasklist_id,
    title="Test child",
    notes="Child notes",
    status=GoogleStatus.todo,
    synced=datetime.now()
)

@pytest.fixture
def setup_tasks():
    print("setup")
    task = test_task_template.google_save()
    child_task = child_task_template.copy()
    child_task.parent = task.google_id
    child_task = child_task.google_save()
    yield
    child_task.google_delete()
    task.google_delete()
    print("teardown")