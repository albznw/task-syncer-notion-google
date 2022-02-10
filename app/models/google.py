from os import path
from enum import Enum
from datetime import datetime
from typing import List, Tuple

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from mongomantic import MongoDBModel

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/tasks']

creds = None
# The file token.json stores the user's access and refresh tokens, and is
# created automatically when the authorization flow completes for the first
# time.

dirname = path.dirname(__file__)
credentials_path = path.join(dirname, "../google_api_credentials.json")
token_path = path.join(dirname, "../token.json")
if path.exists(credentials_path) and path.exists(token_path):
    creds = Credentials.from_authorized_user_file(token_path, SCOPES)
# If there are no (valid) credentials available, let the user log in.
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        raise RuntimeError("You have to setup Google credentials by running google_setup.py manually")
    # Save the credentials for the next run
    with open(token_path, 'w') as token:
        token.write(creds.to_json())

client = build("tasks", "v1", credentials=creds)


def to_python_timestamp(google_timestamp) -> datetime:
    return datetime.strptime(google_timestamp, '%Y-%m-%dT%H:%M:%S.%fZ')

def to_google_timestamp(timestamp: datetime) -> str:
    return timestamp.strftime('%Y-%m-%dT%H:%M:%S.%fZ')


def fetch_google_tasklis_ids() -> List[str]:
    """Fetches up to 100 tasklist ids from Google"""
    res = client.tasklists().list(maxResults=100).execute()
    return list(map(lambda lists_res: lists_res["id"], res["items"]))


class GoogleStatus(str, Enum):
    done = "completed"
    todo = "needsAction"


class GoogleTaskList(MongoDBModel):
    tasklist: str
    title: str

class GoogleTask(MongoDBModel):
    tasklist: str
    title: str
    status: GoogleStatus
    google_id: str | None = None
    due: datetime | None = None
    notes: str | None = None
    parent: str | None = None
    updated: datetime | None = None
    

    # Metafields
    synced: datetime | None = None
    notion_id: str | None = None

    class Meta:
        google_fields = [
            "title", "due", "notes", "status", "parent", "updated"
        ]
        internal_fields = ["id", "synced", "notion_id"]

    @classmethod
    def google_to_kwargs(cls, tasklist_id: str, response: dict) -> dict:
        """Creates a GoogleTask form the Google task response

        Args:
            tasklist_id (str): Tasklist id
            response (dict): The Google task response
        """
        params = {
            "google_id": response["id"],
            "tasklist": tasklist_id
        }

        for field_name in cls.Meta.google_fields:
            if google_field := response.get(field_name):
                if field_name in ["due", "updated"]:
                    params[field_name] = to_python_timestamp(response[field_name])
                else:
                    params[field_name] = google_field

        return params

    @classmethod
    def from_google(cls, tasklist_id: str, google_task: dict):
        """Creates a GoogleTask from the google task response"""
        return cls(**cls.google_to_kwargs(tasklist_id, google_task))

    @classmethod
    def from_dict(cls, params:dict):
        """Creates a GoogleTask from a dictionary"""
        return cls(**params)

    def to_google(self) -> Tuple[str, dict]:
        """Creates the google query neccessary to update the Google task
        """
        return {
            "id": self.google_id,
            "title": self.title,
            "status": self.status,
            "notes": self.notes if self.notes else "",
            "parent": self.parent,
            "due": to_google_timestamp(self.due) if self.due else None
        }

    def google_save(self):
        """Saves the google task to Google. If the task already exists, it's
        updated. Otherwise it's created. Returns the new task.
        """
        # Does the task exist already on Google?
        body = self.to_google()
        if self.google_id:
            # Update the task
            res = client.tasks().update(tasklist=self.tasklist, task=self.google_id, body=body).execute()
        else:
            # Create the task
            res = client.tasks().insert(tasklist=self.tasklist, body=body, parent=self.parent).execute()
        
        new_params = self.google_to_kwargs(self.tasklist, res)
        old_params = self.dict()

        for field in self.Meta.internal_fields:
            new_params[field] = old_params[field]

        return self.from_dict(new_params)

    def google_delete(self):
        """Delete the google task in Google.

        Raises:
            RuntimeError: If the given task does not have a google_id
        """
        if self.google_id:
            client.tasks().delete(tasklist=self.tasklist, task=self.google_id).execute()
        else:
            raise RuntimeError("The google id is not present")

    def move(self, parent:str=None):
        """Moves the task to a new parent or to root of parent is set to None
        Returns a new instance of the task. 

        Returns:
            [GoogleTask]: A new instance of the moved Google task

        Raises:
            RuntimeError: If the parent task id is invalid
        """
        try:
            res = client.tasks().move(
                tasklist=self.tasklist,
                task=self.google_id,
                parent=parent
            ).execute()

            new_params = self.google_to_kwargs(self.tasklist, res)
            old_params = self.dict()

            for field in self.Meta.internal_fields:
                new_params[field] = old_params[field]

            return self.from_dict(new_params)

        except:
            raise RuntimeError("Invalid parent id")
    
    def update_from_params(self, params: dict):
        """Takes a set of params that will override the current fields in a new
        instance of this class.

        Note this function does not update Notion nor does it update the mongo
        db.
        
        Returns:
            [GoogleTask]: An updated instance of this task
        """
        new_params = self.dict()

        for field in params.keys():
            new_params[field] = params[field]

        return self.from_dict(new_params)

    def fetch(self):
        """Fetches this GoogleTask from Google and returns an updated version"""
        google_res = client.tasks().get(tasklist=self.tasklist, task=self.google_id).execute()
        new_params = self.google_to_kwargs(self.tasklist, google_res)
        old_params = self.dict()

        for field in self.Meta.internal_fields:
            new_params[field] = old_params[field]

        updated_task = GoogleTask.from_dict(new_params)
        return updated_task

class GoogleTaskLists(MongoDBModel):

    class Meta:
        model: GoogleTaskList = GoogleTaskList

    @classmethod
    def list(cls, **kwargs):
        """Returns a generator function of the task lists in Google
        
        Yields:
            [GoogleTaskList]: One task list at a time
        """
        res = client.tasklists().list(maxResults=100, **kwargs).execute()
        if items := res.get("items"):
            for tasklist in items:
                try:
                    yield cls.Meta.model(
                        tasklist=tasklist["id"],
                        title=tasklist["title"]
                    )
                except GeneratorExit:
                    pass

    @classmethod
    def get(cls, id:str=None, title:str=None) -> GoogleTaskList:
        if id:
            res = client.tasklists().get(tasklist=id).execute()
            return cls.Meta.model(
                tasklist=res["id"],
                title=res["title"]
            )

        for tasklist in cls.list():
            if tasklist.title == title:
                return tasklist


class GoogleTasks(MongoDBModel):
    class Meta:
        model: GoogleTask = GoogleTask
        tasklists: List[GoogleTaskList] = list(GoogleTaskLists().list())

    @classmethod
    def list(cls, tasklist_id:str= None, **kwargs):
        """Returns a generator function of the tasks of the given tasklist. If
        no tasklist is specified all tasks are returned.

        Yields:
            [GoogleTask]: On task at a time
        """
        if tasklist_id:
            tasklists_ids = [tasklist_id]
        else:
            tasklists_ids = [tasklist.tasklist for tasklist in cls.Meta.tasklists]

        for tasklist_id in tasklists_ids:
            google_res = client.tasks().list(tasklist=tasklist_id, maxResults=100, **kwargs).execute()
            if google_res.get("items"):
                for task in google_res["items"]:
                    try:
                        yield cls.Meta.model.from_google(
                            tasklist_id=tasklist_id, google_task=task)
                    except GeneratorExit:
                        pass
            else:
                return []
    
    @classmethod
    def get(cls, tasklist_id: str, task_id: str, **kwargs) -> GoogleTask:
        res = client.tasks().get(tasklist=tasklist_id, task=task_id, **kwargs).execute()
        return GoogleTask.from_google(tasklist_id=tasklist_id, google_task=res)
