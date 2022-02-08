from app.models.mongo import GoogleTaskRepository, NotionTaskRepository
from app.tests.fixtures import mongo_fixture
from app.tests.fixtures.notion import setup_notion_test_tasks
from app.models.google import GoogleStatus, GoogleTask
from app.models.notion import NotionTask
from app.config import settings

class TestNotionTaskRepository:
    def test_mongo(self, mongo_fixture, setup_notion_test_tasks):
        task_before_save, _ = setup_notion_test_tasks
        NotionTaskRepository.save(task_before_save)

        task_gen = NotionTaskRepository.find()
        mongo_tasks = [t for t in task_gen]

        assert len(mongo_tasks) == 1
        assert isinstance(mongo_tasks[0], NotionTask)
        assert mongo_tasks[0].dict(exclude={"id"}) == task_before_save.dict(exclude={"id"})


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
