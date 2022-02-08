from datetime import datetime
from typing import List
from app.models.google import GoogleTask

from app.models.notion import NotionTask, NotionTasks
from app.models.mongo import GoogleTaskRepository, NotionTaskRepository
from app.converters import notion_to_google_task
from app.config import settings


logger = settings.logger

class NotionSyncer:

    last_sync: datetime
    synced_tasks: List[NotionTask]

    def __init__(self) -> None:
        self.last_sync = None
        self.synced_tasks = []

    def sync_task(self, n_task: NotionTask, fix_parent=True) -> NotionTask:
        logger.debug(f'Syncing task "{n_task.title}"')

        try:
            # Check if task exists internally
            i_task: NotionTask = next(NotionTaskRepository.find(notion_id=n_task.notion_id))

            if n_task.updated > i_task.updated:
                # The Notion task is newer, update internal tasks
                # Should trigger an update at Google as well
                logger.debug("--> Updating task from Notion")
                i_task = i_task.fetch()
                i_task.synced = datetime.now()
                i_google_task: GoogleTask = next(GoogleTaskRepository.find(google_id=i_task.google_id))

                i_google_task = i_google_task.update_from_params(
                    notion_to_google_task(i_task).dict(
                        exclude={*GoogleTask.Meta.internal_fields}
                    )
                )
                i_google_task = i_google_task.google_save()
                i_task = NotionTaskRepository.save(i_task)
                i_google_task = GoogleTaskRepository.save(i_google_task)
                return i_task

            elif n_task.updated < i_task.updated:
                logger.debug("<-- Updating Notion task")
                google_task: GoogleTask = next(GoogleTaskRepository.find(
                    google_id=i_task.google_id))
                i_task.notion_save()

                sync_time = datetime.now()
                i_task.synced = sync_time
                google_task.synced = sync_time

                i_task = NotionTaskRepository.save(i_task)
                google_task = GoogleTaskRepository.save(google_task)
                return i_task
            
            else:
                # Up to date!
                return i_task

        except:
            logger.debug('--> New task')

            try:
                n_task.synced = datetime.now()
                google_task = notion_to_google_task(n_task)
                google_task = google_task.google_save()
                
                n_task.google_id = google_task.google_id
                n_task = NotionTaskRepository.save(n_task)
                google_task = GoogleTaskRepository.save(google_task)
                return n_task

            except RuntimeError:
                if fix_parent:
                    # Get parent task from Notion and sync parent
                    notion_parent_task = NotionTasks.get(n_task.parent_task_ids[0])
                    synced_parent = self.sync_task(notion_parent_task)
                    self.synced_tasks.append(synced_parent)

                    # Try again
                    return self.sync_task(n_task)
                
                else:
                    logger.warn("Parent task did not exist in Google, jumping this one for now")
                    return


    def sync(self):
        logger.info('Syncing tasks FROM Notion')
        self.synced_tasks = []

        for n_task in NotionTasks().list():
            synced_task = self.sync_task(n_task)
            self.synced_tasks.append(synced_task)

        synced_task_ids = [task.notion_id for task in self.synced_tasks]

        for i_task in NotionTaskRepository.find():
            if i_task.notion_id not in synced_task_ids:
                # Remove internal task, this should remove the internal-
                # and external Google task as well 
                logger.debug('--x ({i_task.title}) Task removed in Notion')
                try:
                    i_google_task: GoogleTask = next(GoogleTaskRepository.find(
                        google_id=i_task.google_id))
                    i_google_task.google_delete()
                    g_deleted = GoogleTaskRepository._get_collection().delete_one({"google_id": i_google_task.google_id})
                    n_deleted = NotionTaskRepository._get_collection().delete_one({"notion_id": i_task.notion_id})

                    if n_deleted.deleted_count == 0:
                        logger.error(f'Could not delete the corresponding internal Notion task of "{i_task.title}" (nid={i_task.notion_id})')
                    if g_deleted.deleted_count == 0:
                        logger.error(f'Could not delete the corresponding internal Google task of "{i_google_task.title}" (gid={i_google_task.google_id})')
                    
                except:
                    logger.error("Could not remove task internally or in Google")

        self.last_sync = datetime.now()
