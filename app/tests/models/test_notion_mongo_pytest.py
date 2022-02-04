from app.models.mongo import NotionTaskRepository
from app.models.notion import NotionTask, NotionTaskDB
from app.tests.fixtures import db_fixture


def test_mongo(db_fixture):
    task_before_save = next(NotionTaskDB().list())
    NotionTaskRepository.save(task_before_save)


    task_gen = NotionTaskRepository.find()
    mongo_tasks = [t for t in task_gen]

    assert len(mongo_tasks) == 1
    assert isinstance(mongo_tasks[0], NotionTask)
    assert task_before_save.dict(exclude={"id"}) == mongo_tasks[0].dict(exclude={"id"})