from app.models.mongo import GoogleTaskRepository, NotionTaskRepository
from app.tests.fixtures import mongo_fixture
from app.tests.fixtures.notion import setup_notion_test_tasks
from app.models.google import GoogleStatus, GoogleTask
from app.models.notion import NotionTask
from app.config import settings

class TestNotionTaskRepository:
    def test_mongo(self, mongo_fixture, setup_notion_test_tasks):
        task_before_save, _ = setup_notion_test_tasks
        task_after_save = NotionTaskRepository.save(task_before_save)

        assert task_after_save.dict(exclude={"id"}) == task_before_save.dict(exclude={"id"})

        internal_tasks = list(NotionTaskRepository.find())
        assert len(internal_tasks) == 1
        assert isinstance(internal_tasks[0], NotionTask)

        # MongoDB Fetched task, should have the same values
        assert internal_tasks[0].dict(exclude={"id", "due"}) == task_after_save.dict(exclude={"id", "due"})
        assert internal_tasks[0].to_notion_kwargs() == task_after_save.to_notion_kwargs()




class TestGoogleTaskRepository:
    def test_mongo(self, mongo_fixture):
        # Create Google task
        task_before_save = GoogleTask(
            title="Testtask",
            status=GoogleStatus.todo,
            tasklist=settings.google_default_tasklist
        ).google_save()

        saved_task = GoogleTaskRepository.save(task_before_save)

        assert isinstance(saved_task, GoogleTask)
        assert saved_task.dict(exclude={"id"}) == task_before_save.dict(exclude={"id"})
