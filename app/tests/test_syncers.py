from app.models.mongo import NotionTaskRepository, GoogleTaskRepository
from app.models.notion import NotionBuckets, NotionTask, NotionTasks
from app.models.google import GoogleTasks, GoogleTask
from app.syncers.google import GoogleSyncer
from app.syncers.notion import NotionSyncer
from app.tests.fixtures import mongo_fixture
from app.tests.fixtures.notion import setup_notion_test_tasks, parent_params
from app.tests.fixtures.google import test_task_template
from app.config import settings


class TestGoogleSyncer:
    def test_create_and_remove_task_in_google(self, mongo_fixture):
        dev_tasklist = settings.google_default_tasklist
        # Make sure both databases are empty before we start
        assert len(list(GoogleTasks().list(tasklist_id=dev_tasklist))) == 0
        assert len(list(GoogleTaskRepository.find())) == 0

        task = test_task_template.google_save()

        syncer = GoogleSyncer()
        syncer.sync(tasklists=[dev_tasklist], sync_notion=False)
        assert len(list(GoogleTasks().list(tasklist_id=dev_tasklist))) == 1
        assert len(list(GoogleTaskRepository.find())) == 1

        task = task.google_delete()
        syncer.sync(tasklists=[dev_tasklist], sync_notion=False)
        assert len(list(GoogleTasks().list(tasklist_id=dev_tasklist))) == 0
        assert len(list(GoogleTaskRepository.find())) == 0

    def test_create_and_remove_end_to_end_google_notion(self):
        # Make sure both databases are empty before we start
        dev_tasklist = settings.google_default_tasklist
        dev_bucket_id = NotionBuckets().get_by_title("Dev").notion_id
        notion_tasks_filter = {"property": "Bucket", "relation": {"contains": dev_bucket_id}}
        
        assert len(list(GoogleTasks().list(tasklist_id=dev_tasklist))) == 0
        assert len(list(GoogleTaskRepository.find())) == 0
        assert len(list(NotionTaskRepository.find())) == 0
        assert len(list(NotionTasks().list(filter=notion_tasks_filter))) == 0

        task = test_task_template.google_save()

        syncer = GoogleSyncer()
        syncer.sync(tasklists=[dev_tasklist])
        assert len(list(GoogleTasks().list(tasklist_id=dev_tasklist))) == 1
        assert len(list(GoogleTaskRepository.find())) == 1
        assert len(list(NotionTaskRepository.find())) == 1
        assert len(list(NotionTasks().list(filter=notion_tasks_filter))) == 1

        task = task.google_delete()
        syncer.sync(tasklists=[dev_tasklist])
        assert len(list(GoogleTasks().list(tasklist_id=dev_tasklist))) == 0
        assert len(list(GoogleTaskRepository.find())) == 0
        assert len(list(NotionTaskRepository.find())) == 0
        assert len(list(NotionTasks().list(filter=notion_tasks_filter))) == 0

class TestNotionSyncer:

    def test_create_and_remove_task_in_notion(self, mongo_fixture):
        # Make sure both databases are empty before we start
        assert len(list(NotionTasks().list())) == 0
        assert len(list(NotionTaskRepository.find())) == 0

        task = NotionTask(**parent_params)
        task = task.notion_save()

        syncer = NotionSyncer()
        syncer.sync(sync_google=False)
        assert len(list(NotionTasks().list())) == 1
        assert len(list(NotionTaskRepository.find())) == 1

        task = task.notion_delete()
        syncer.sync(sync_google=False)
        assert len(list(NotionTasks().list())) == 0
        assert len(list(NotionTaskRepository.find())) == 0


    def test_create_and_remove_end_to_end_notion_google(self):
        # Make sure both databases are empty before we start
        dev_tasklist = settings.google_default_tasklist
        dev_bucket_id = NotionBuckets().get_by_title("Dev").notion_id 
        notion_tasks_filter = {"property": "Bucket", "relation": {"contains": dev_bucket_id}}

        assert len(list(GoogleTasks().list(tasklist_id=dev_tasklist))) == 0
        assert len(list(GoogleTaskRepository.find())) == 0
        assert len(list(NotionTaskRepository.find())) == 0
        assert len(list(NotionTasks().list(filter=notion_tasks_filter))) == 0

        # set dev bucket
        parent_params["bucket_id"] = dev_bucket_id
        task = NotionTask(**parent_params)
        task = task.notion_save()

        syncer = NotionSyncer()
        syncer.sync()
        assert len(list(GoogleTasks().list(tasklist_id=dev_tasklist))) == 1
        assert len(list(GoogleTaskRepository.find())) == 1
        assert len(list(NotionTaskRepository.find())) == 1
        assert len(list(NotionTasks().list(filter=notion_tasks_filter))) == 1

        task = task.notion_delete()
        syncer.sync()
        assert len(list(GoogleTasks().list(tasklist_id=dev_tasklist))) == 0
        assert len(list(GoogleTaskRepository.find())) == 0
        assert len(list(NotionTaskRepository.find())) == 0
        assert len(list(NotionTasks().list(filter=notion_tasks_filter))) == 0