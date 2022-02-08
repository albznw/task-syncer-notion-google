from app.models.mongo import GoogleTaskRepository, NotionTaskRepository
from app.models.notion import NotionBuckets, NotionStatus, NotionTask, NotionTime
from app.models.google import GoogleStatus, GoogleTask, GoogleTaskLists, GoogleTasks
from app.config import settings

notion_todo = NotionStatus(
    notion_id="c062eac1-aff7-4c30-b4bb-76656a4c5495", name="ToDo", color="red")
notion_ongoing_task = NotionStatus(
    notion_id="be9a06e6-c0e8-428c-bfdd-17a3fd895a74", name="Ongoing task", color="green")
notion_ongoing_project = NotionStatus(
    notion_id="a172d018-fe50-4f53-acad-486e204c42a4", name="Ongoing project", color="purple")
notion_done = NotionStatus(
    notion_id="8be52672-830d-4447-86d2-1072bb266d92", name="Done", color="orange")

status_mapper = [
    {"google": GoogleStatus.todo, "notion": notion_todo},
    {"google": GoogleStatus.todo, "notion": notion_ongoing_task},
    {"google": GoogleStatus.todo, "notion": notion_ongoing_project},
    {"google": GoogleStatus.done, "notion": notion_done},
]


def notion_to_google_status(n_status: NotionStatus) -> GoogleStatus:
    for status in status_mapper:
        if status["notion"] == n_status:
            return status["google"]

    # Default to "todo"
    return GoogleStatus.todo

def google_to_notion_status(g_status: GoogleStatus) -> NotionStatus | None:
    for status in status_mapper:
        if status["google"] == g_status:
            return status["notion"]


def notion_to_google_task(n_task: NotionTask) -> GoogleTask:
    """Converts a NotionTask to a GoogleTask. Note, it only takes the fields
    present in both models. NotionTask-model specific fields will not get converted.

    Args:
        n_task (NotionTask): The Notion task

    Returns:
        [GoogleTask]: An instance of a GoogleTask version of sent task
    """
    tasklist_id = GoogleTaskLists.get(
        title=NotionBuckets.get(n_task.bucket_id).title).tasklist

    g_parent_id = None
    if n_task.parent_task_ids:
        # Notion task has a parent, let's find the Google parent. It should
        # be in Google's version of the Notion bucket.
        try:
            n_parent: NotionTask = next(
                NotionTaskRepository.find(notion_id=n_task.parent_task_ids[0]))
            g_parent: GoogleTask = next(
                GoogleTaskRepository.find(
                    tasklist=tasklist_id, google_id=n_parent.google_id
                ))
            g_parent_id = g_parent.google_id
        except:
            raise RuntimeError("Parent task did not exist internaly")

    google_params = {
        "google_id": n_task.google_id,
        "tasklist": tasklist_id,
        "title": n_task.title,
        "notes": n_task.notes,
        "status": notion_to_google_status(n_task.status),
        "parent": g_parent_id,
        "due": n_task.due.datetime(),
        "synced": n_task.synced,
        "notion_id": n_task.notion_id,
    }

    g_task = GoogleTask(**google_params)
    return g_task


def google_to_notion_task(g_task: GoogleTask) -> NotionTask:
    """Converts a GoogleTask to a NotionTask. Note, it only takes the fields
    present in both models. GoogleTask-model specific fields will not get converted. For example, the labels field that is present i NotionTasks

    Args:
        n_task (GoogleTask): The Google task

    Returns:
        [NotionTask]: An instance of a NotionTask version of sent task
    """

    bucket_id = NotionBuckets().get_by_title(
        title=GoogleTaskLists.get(id=g_task.tasklist).title).notion_id

    n_parents = []
    if g_task.parent:
        # Google task has a parent, let's find the Notion parent.
        try:
            g_parent: GoogleTask = next(
                GoogleTaskRepository.find(google_id=g_task.parent))
            n_parent: NotionTask = next(
                NotionTaskRepository.find(notion_id=g_parent.notion_id))
            n_parents = [n_parent.notion_id]
        except:
            raise RuntimeError("Parent task did not exist internally")

    due = None
    if g_task.due:
        due = NotionTime(dt=g_task.due, has_time=False)

    notion_params = {
        "notion_id": g_task.notion_id,
        "title": g_task.title,
        "notes": g_task.notes,
        "status": google_to_notion_status(g_task.status),
        "bucket_id": bucket_id,
        "parent_task_ids": n_parents,
        "due": due,
        "database_id": settings.notion_task_db,
        "synced": g_task.synced,
        "google_id": g_task.google_id,
    }

    n_task = NotionTask(**notion_params)
    return n_task
