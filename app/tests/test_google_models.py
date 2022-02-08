import pytest
from datetime import datetime, date

from app.models.google import GoogleTaskList, GoogleTaskLists, GoogleTasks, GoogleTask, GoogleStatus
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


########################## Test the GoogleTask model ###########################

class TestGoogleTask:
    def test_create(self):
        tasks = list(GoogleTasks.list(tasklist_id=dev_tasklist_id))
        assert len(tasks) == 0

        new_task = test_task_template.google_save()

        tasks = list(GoogleTasks.list(tasklist_id=dev_tasklist_id))
        assert len(tasks) == 1

        assert isinstance(new_task.google_id, str)

        for field in ["tasklist", "title", "due", "notes", "status", "synced"]:
            assert test_task_template.__getattribute__(field) == new_task.__getattribute__(field)

        new_task.google_delete()

        tasks = list(GoogleTasks.list(tasklist_id=dev_tasklist_id))
        assert len(tasks) == 0

    def test_create_subtask(self):
        parent_task = test_task_template.google_save()

        child_task = child_task_template.copy()
        child_task.parent = parent_task.google_id
        child_task = child_task.google_save()

        assert isinstance(child_task.google_id, str)

        for field in ["tasklist", "title", "due", "notes", "status", "synced"]:
            assert child_task.__getattribute__(field) == child_task_template.__getattribute__(field)
        
        assert child_task.parent == parent_task.google_id

        parent_task.google_delete()

    def test_move(self):
        parent_task = test_task_template.google_save()
        child_task = child_task_template.google_save()
        assert child_task.parent == None

        # Move to parent
        parent_id = parent_task.google_id
        child_task = child_task.move(parent_id)
        assert child_task.parent == parent_id

        # Move to root
        child_task = child_task.move(None)
        assert child_task.parent == None

        # Remove parent and then move subtask to removed parent
        parent_task.google_delete()
        with pytest.raises(RuntimeError):
            child_task.move(parent_id)

    def test_update_fields(self):
        task = test_task_template.google_save()

        task.due = None
        task.synced = datetime(year=2022, month=2, day=16)

        updated_task = task.google_save()

        for field in ["tasklist", "title", "notes", "status", "synced"]:
            assert updated_task.__getattribute__(field) == task.__getattribute__(field)

        updated_task.google_delete()


######################## Test the GoogleTaskLists model ########################

class TestGoogleTaskLists:
    def test_list_google_task_lists(self):
        lists = list(GoogleTaskLists.list())
        assert len(lists) > 0
        assert isinstance(lists[0], GoogleTaskList)


########################## Test the GoogleTasks model ##########################
# The one used for listing tasks and fetching tasks

class TestGoogleTasks:
    def test_meta_class(self):
        g_tasks = GoogleTasks()
        assert isinstance(g_tasks.Meta.tasklists[0], GoogleTaskList)

    def test_list_dev_tasks(self, setup_tasks):
        tasks = list(GoogleTasks.list(dev_tasklist_id))
        assert len(tasks) == 2

    def test_list_all_tasks(self):
        tasks = list(GoogleTasks.list())
        assert len(tasks) > 0
