

from datetime import datetime
from typing import List

from app.models.google import GoogleTask, GoogleTasks
from app.models.notion import NotionTask
from app.models.mongo import GoogleTaskRepository, NotionTaskRepository
from app.converters import google_to_notion_task
from app.config import settings

logger = settings.logger

class GoogleSyncer:

    last_sync: datetime
    synced_tasks: List[GoogleTask]

    def __init__(self) -> None:
        self.last_sync = None
        self.synced_tasks = []

    def sync_task(self, g_task: GoogleTask, fix_parent=True, sync_notion=True) -> GoogleTask:
        logger.debug(f'Syncing task "{g_task.title}"')

        try:
            # Check if the task exists internally
            i_task: GoogleTask = next(GoogleTaskRepository.find(google_id=g_task.google_id))

            if g_task.updated > i_task.updated:
                # The Google task is newer, update internal tasks
                # Should trigger an update at Notion as well
                logger.debug("--> Updating task from Google")
                i_task = i_task.fetch()
                i_task.synced = datetime.now()
                
                if sync_notion:
                    old_i_notion_task: NotionTask = next(NotionTaskRepository.find(notion_id=i_task.notion_id))

                    i_notion_task = old_i_notion_task.update_from_params(
                        google_to_notion_task(i_task).dict(
                            exclude={*NotionTask.Meta.internal_fields, "updated", "subtask_ids"}
                        )
                    )

                    i_notion_task = i_notion_task.notion_save()
                    i_notion_task = NotionTaskRepository.update(i_notion_task)

                i_task = GoogleTaskRepository.update(i_task)
                return i_task

            elif g_task.updated < i_task.updated:
                logger.debug("<-- Updating Google task")
                i_task.google_save()
                
                sync_time = datetime.now()
                i_task.synced = sync_time

                if sync_notion:
                    notion_task: NotionTask = next(NotionTaskRepository.find(
                        notion_id=i_task.notion_id
                    ))
                    notion_task.synced = sync_time
                    notion_task = NotionTaskRepository.update(notion_task)

                i_task = GoogleTaskRepository.update(i_task)
                return i_task
            
            else:
                # Up to date!
                return i_task

        except:
            logger.debug('--> New task')

            try:
                g_task.synced = datetime.now()
                
                if sync_notion:
                    notion_task = google_to_notion_task(g_task)
                    notion_task = notion_task.notion_save()

                    if notion_task.parent_task_ids:
                        # Newly created task has parents, update them internally
                        parent_task = next(NotionTaskRepository.find(notion_id=notion_task.parent_task_ids[0]))
                        parent_task = parent_task.fetch()
                        NotionTaskRepository.update(parent_task)

                    g_task.notion_id = notion_task.notion_id
                    notion_task = NotionTaskRepository.save(notion_task)

                g_task = GoogleTaskRepository.save(g_task)
                return g_task

            except RuntimeError:
                if fix_parent:
                    logger.info("Parent error, fixing parent")
                    # Get parent task from Google and sync parent
                    google_parent_task = GoogleTasks.get(
                        g_task.tasklist, g_task.parent)
                    synced_parent = self.sync_task(google_parent_task, sync_notion=sync_notion)
                    self.synced_tasks.append(synced_parent)

                    # Try again
                    return self.sync_task(g_task, sync_notion=sync_notion)

                else:
                    logger.warn("Parent task did not exist in Notion, jumping this one for now")
                    return

    def sync(self, tasklists:List[str]=None, sync_notion=True):
        logger.debug("Syncing tasks FROM Google")
        self.synced_tasks = []
        google_tasks_to_sync = []

        if tasklists:
            for tasklist_id in tasklists:
                google_tasks_to_sync += list(GoogleTasks.list(tasklist_id=tasklist_id))
        else:
            google_tasks_to_sync = list(GoogleTasks.list())

        for g_task in google_tasks_to_sync:
            synced_task = self.sync_task(g_task, sync_notion=sync_notion)
            self.synced_tasks.append(synced_task)

        synced_task_ids = [task.google_id for task in self.synced_tasks]

        for i_task in GoogleTaskRepository.find():
            if i_task.google_id not in synced_task_ids:
                # Remove internal task, this should remove the internal-
                # and external Notion task as well
                logger.debug(f'--x ({i_task.title}) Task removed in Google')
                try:
                    if sync_notion:
                        i_notion_task: NotionTask = next(NotionTaskRepository.find(
                            notion_id=i_task.notion_id
                        ))
                        i_notion_task.notion_delete()
                        n_deleted = NotionTaskRepository._get_collection().delete_one({"notion_id": i_notion_task.notion_id})

                        if n_deleted.deleted_count == 0:
                            logger.error(f'Could not delete the corresponding internal Notion task of "{i_notion_task.title}" (nid={i_notion_task.notion_id})')
                    
                    g_deleted = GoogleTaskRepository._get_collection().delete_one({"google_id": i_task.google_id})

                    if g_deleted.deleted_count == 0:
                        logger.error(f'Could not delete the corresponding internal Google task of "{i_task.title}" (gid={i_task.google_id})')

                except:
                    logger.error(f'Could not find the internal NotionTask of task "{i_task.title}" (gid={i_task.google_id})')

        self.last_sync = datetime.now()
