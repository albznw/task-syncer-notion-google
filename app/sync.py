from datetime import datetime, timezone, timedelta
from typing import List

from pydantic import constr
from app.models.notion import NotionBucket, NotionStatus, NotionStatuses, NotionTask, NotionTime
from app.config import settings
from app.models.google import GoogleList, GoogleStatus, GoogleTask
from app.models.mapper import TasksMapper, ListBucketMapper

notion_tasks_db_id = settings.notion_task_db

def construct_google_task_from_notion(g_tasklist: str, n_task: NotionTask) -> GoogleTask:
    params = {
        "tasklist": g_tasklist,
        "title": n_task.title,
        "notes": n_task.details,
    }

    params["status"] = GoogleStatus.todo
    if n_task.status and n_task.status.id == "8be52672-830d-4447-86d2-1072bb266d92":
        params["status"] = GoogleStatus.done

    if n_task.due:
        params["due"] = n_task.due.datetime()

    return GoogleTask(**params)

def create_google_task_from_notion(g_tasklist: str, n_task: NotionTask) -> GoogleTask:
    return construct_google_task_from_notion(g_tasklist, n_task).create()

def update_google_task_from_notion(n_task: NotionTask, g_task: GoogleTask):
    g_task.title = n_task.title
    g_task.notes = n_task.details

    g_task.status = GoogleStatus.todo
    if n_task.status and n_task.status.id == "8be52672-830d-4447-86d2-1072bb266d92":
        g_task.status = GoogleStatus.done

    g_task.due = None
    if n_task.due:
        g_task.due = n_task.due.datetime()

    if not n_task.parent_tasks and g_task.parent:
        # Task has moved out from parent to itself
        g_task.move_parent(None)

    if n_task.parent_tasks and not g_task.parent:
        # Task has moved to NEW parent
        # Fetch Google task if it exists. Otherwise, update next time
        if task_mapper := TasksMapper.get(notion_id=n_task.parent_tasks[0]):
            g_task.move_parent(task_mapper.google_id)  # Might raise exception
        else:
            raise Exception("Google parent task does not exist")

    if n_task.parent_tasks and g_task.parent:
        # Check if it's still the same parent task
        task_mapper = TasksMapper.get(notion_id=n_task.parent_tasks[0])
        if task_mapper.google_id != g_task.parent:
            # Task has move to other parent
            g_task.move_parent(task_mapper.google_id)  # Might raise exception

    return g_task.update()

def construct_notion_task_from_google(g_task: GoogleTask):
    bucket_id = ListBucketMapper.get(google_id=g_task.tasklist).notion_id

    if g_task.status == GoogleStatus.done:
        status = NotionStatuses().get("8be52672-830d-4447-86d2-1072bb266d92")
    else:
        status = NotionStatuses().get("c062eac1-aff7-4c30-b4bb-76656a4c5495")

    due = None
    if g_task.due:
        due = NotionTime(date=g_task.due.date())

    sync_time = datetime.now(timezone.utc).astimezone()
    
    n_task = NotionTask(
        title=g_task.title,
        bucket=bucket_id,
        details=g_task.notes,
        status=status,
        due=due,
        synced=NotionTime(dateandtime=sync_time),
        database_id=notion_tasks_db_id
    )

    return n_task

def create_notion_task_from_google(g_task: GoogleTask):
    return construct_notion_task_from_google(g_task).create()

def update_notion_task_from_google(g_task: GoogleTask, n_task: NotionTask):
    n_task.title = g_task.title
    n_task.details = g_task.notes

    notion_done_status = NotionStatuses().get("8be52672-830d-4447-86d2-1072bb266d92")

    if g_task.status == GoogleStatus.done:
        n_task.status = notion_done_status
    elif n_task.status == notion_done_status:
        n_task.status = NotionStatuses().get("c062eac1-aff7-4c30-b4bb-76656a4c5495")
        

    if g_task.due:
        n_task.due = NotionTime(date=g_task.due.date())
    else:
        n_task.due = None

    if not g_task.parent and n_task.parent_tasks:
        # Task has moved out from parent to itself
        n_task.parent_tasks = []

    if g_task.parent and not n_task.parent_tasks:
        # Task has moved to NEW parent
        # Fetch Notion task if it exists. Otherwise, update next time
        if task_mapper := TasksMapper.get(google_id=g_task.parent):
            n_task.parent_tasks = [task_mapper.notion_id]
        else:
            raise Exception("Notion parent task does not exist")

    return n_task.update()

def check_change_notion_and_google_tasks(n_task: NotionTask, g_task: GoogleTask):
    if n_task.due:
        due_diff = n_task.due.datetime() - g_task.due
        if due_diff > timedelta(days=1):
            return True

    if n_task.details and g_task.notes:
        if n_task.details != g_task.notes:
            return True

    notion_done_status = NotionStatuses().get("8be52672-830d-4447-86d2-1072bb266d92")

    if not (g_task.status == GoogleStatus.done and n_task.status == notion_done_status):
        return True
    
    if not (g_task.status != GoogleStatus.done and n_task.status != notion_done_status):
        return True

    if n_task.title != g_task.title or \
       not n_task.parent_tasks and g_task.parent or \
       n_task.parent_tasks and not g_task.parent or \
       n_task.parent_tasks and g_task.parent:
           return True


def purge_tasks_notion():
    # Deleted tasks in Google should delete task in Notion
    all_lists = GoogleList.list()
    all_tasks = []
    for g_list in all_lists:
        all_tasks += g_list.tasks()

    removed_tasks = TasksMapper.find(filter={
        "google_id": {
            "$nin": [ task.id for task in all_tasks ]
        }
    })
    for task in removed_tasks:
        NotionTask.delete(task.notion_id)
    count = TasksMapper.delete_many({
        "google_id": {
            "$in": [task.google_id for task in removed_tasks]
        }
    })
    print(f"Removed {count} tasks from Notion that was deleted in Google")

def purge_tasks_google():
    # Deleted tasks in Notion should delete task in Google
    all_tasks = NotionTask.list()
    all_task_ids = [ task.id for task in all_tasks ]
    removed_tasks_mapper: List[TasksMapper] = TasksMapper.find(filter={"notion_id": { "$nin": [task.id for task in all_tasks]}})
    removed_tasks_n_ids = [task.notion_id for task in removed_tasks_mapper]

    removed_task_ids: List[NotionTask] = list(filter(lambda x: x not in all_task_ids, removed_tasks_n_ids))

    for task_n_id in removed_task_ids:
        task = NotionTask.get(task_n_id)
        g_list_mapper = ListBucketMapper.get(notion_id=task.bucket.id)
        g_task_mapper = next(filter(lambda x: x.notion_id == task_n_id, removed_tasks_mapper))
        GoogleTask.delete(g_list_mapper.google_id, g_task_mapper.google_id)
    
    count = TasksMapper.delete_many({
        "notion_id": {
            "$in": removed_tasks_n_ids
        }
    })
    print(f"Removed {count} tasks from Google that was deleted in Notion")


# To Notion
def google_to_notion_sync():
    print("Syncing Google -> Notion")

    g_list: GoogleList = list(filter(lambda x : x.title == "Work", GoogleList.list()))[0]

    all_lists = GoogleList.list()

    for g_list in all_lists: 
        g_tasks = g_list.tasks()

        for g_task in g_tasks:
            mapper = TasksMapper.get(google_id=g_task.id)

            if mapper == None:
                # Notion task does not exist
                n_task = construct_notion_task_from_google(g_task)

                # Check if Google task is a subtask
                if g_task.parent:
                    # Try and fetch Notion parent task
                    parent_mapper = TasksMapper.get(google_id=g_task.parent)
                    if parent_mapper == None:
                        # Parent task did not exit, jump over for now
                        continue
                    else:
                        # Parent task existed
                        n_task.parent_tasks = [parent_mapper.notion_id]

                n_task = n_task.create() # Create Notion task
                sync_time = n_task.synced.datetime()
                TasksMapper(
                    notion_id=n_task.id,
                    notion_sync=sync_time,
                    google_id=g_task.id,
                    google_sync=sync_time
                ).create()

            else:
                # Notion task exists

                # Check if update is needed
                n_task = NotionTask.get(mapper.notion_id)
                if check_change_notion_and_google_tasks(n_task, g_task):
                    sync_time = datetime.now(timezone.utc).astimezone()
                    n_task.synced = NotionTime(dateandtime=sync_time)
                    n_task = update_notion_task_from_google(g_task, n_task)
                    mapper.notion_sync = sync_time
                    mapper.google_sync = sync_time
                    mapper.update()

# To google
def notion_to_google_sync():
    print("Syncing Notion -> Google")
    all_buckets: List[NotionBucket] = NotionBucket.list()
    
    for bucket in all_buckets:
        g_tasklist = ListBucketMapper.get(bucket.id).google_id
        for task_id in bucket.tasks:
            n_task = NotionTask.get(task_id)
            mapper = TasksMapper.get(notion_id=n_task.id)

            if mapper == None:
                # Google task does not exist
                n_task.synced = NotionTime(dateandtime=datetime.now(timezone.utc).astimezone())
                g_task = create_google_task_from_notion(g_tasklist, n_task)

                # Check if Notion task is a subtask
                if n_task.parent_tasks:
                    parent_n_id = n_task.parent_tasks[0]
                    # Try to fetch Google parent task if it exists
                    parent_mapper = TasksMapper.get(notion_id=parent_n_id)
                    if parent_mapper:
                        g_task = g_task.move_parent(parent_mapper.google_id)
                    else:
                        # Parent task does not exist, jump for now
                        continue

                TasksMapper(
                    notion_id=n_task.id,
                    notion_sync=n_task.synced.datetime(),
                    google_id=g_task.id,
                    google_sync=n_task.synced.datetime()
                ).create()
                n_task = n_task.update()

            else:
                # Google task exists

                # Check if update is needed
                if n_task.synced == None or n_task.synced.datetime() < n_task.updated.datetime(): 
                    # Get google task
                    n_task.synced = NotionTime(dateandtime=datetime.now(timezone.utc).astimezone())
                    g_task = GoogleTask.get(g_tasklist, mapper.google_id)
                    try:
                        g_task = update_google_task_from_notion(n_task, g_task)
                    except:
                        continue
                    n_task = n_task.update()
                    mapper.notion_sync = n_task.synced.datetime()
                    mapper.google_sync = n_task.synced.datetime()
                    mapper.update()
