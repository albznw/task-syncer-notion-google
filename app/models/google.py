from datetime import datetime
from enum import Enum
from os import path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from pydantic import BaseModel

from app.models.notion import NotionTask

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
        flow = InstalledAppFlow.from_client_secrets_file(
            credentials_path, SCOPES)
        creds = flow.run_local_server(port=8080)
    # Save the credentials for the next run
    with open(token_path, 'w') as token:
        token.write(creds.to_json())

client = build("tasks", "v1", credentials=creds)

def google_to_python_timestamp(google_timestamp) -> datetime:
    return datetime.strptime(google_timestamp, '%Y-%m-%dT%H:%M:%S.%fZ')

class GoogleStatus(str, Enum):
    done = "completed"
    todo = "needsAction"

class GoogleTask(BaseModel):
    id: str | None = None
    tasklist: str
    title: str
    due: datetime | None = None
    notes: str | None = None
    status: GoogleStatus
    parent: str | None = None
    updated: datetime | None = None

    @classmethod
    def from_google(cls, tasklist: str, google_task: dict):

        if google_task.get("due"):
            google_task["due"] = google_to_python_timestamp(google_task["due"])

        google_task["updated"] = google_to_python_timestamp(google_task["updated"])

        return cls(tasklist=tasklist, **google_task)

    @classmethod
    def list(cls, tasklist: str):
        resp = client.tasks().list(tasklist=tasklist).execute()
        tasks = []
        for task in resp["items"]:
            tasks.append(cls.from_google(tasklist, task))
        return tasks

    @classmethod
    def get(cls, tasklist: str, id: str):
        resp = client.tasks().get(tasklist=tasklist, task=id).execute()
        return cls.from_google(tasklist, resp)

    @classmethod
    def delete(cls, tasklist: str, id: str):
        resp = client.tasks().delete(tasklist=tasklist, task=id).execute()
        return resp

    def delete_self(self):
        resp = client.tasks().delete(tasklist=self.tasklist, task=self.id).execute()
        return resp

    def create(self):
        res = client.tasks().insert(tasklist=self.tasklist, body={
            "title": self.title,
            "due": self.due.strftime('%Y-%m-%dT%H:%M:%S.%fZ') if self.due else None,
            "notes": self.notes,
            "status": self.status,
        }).execute()

        return self.from_google(self.tasklist, res)

    def update(self):
        res = client.tasks().update(
            tasklist=self.tasklist,
            task=self.id,
            body={
                "id": self.id,
                "title": self.title,
                "due": self.due.strftime('%Y-%m-%dT%H:%M:%S.%fZ') if self.due else None,
                "notes": self.notes,
                "status": self.status,
                "parent": self.parent,
            }
        ).execute()

        return self.from_google(self.tasklist, res)

    def move_parent(self, parent_id: str | None):
        res = client.tasks().move(
            tasklist=self.tasklist,
            task=self.id,
            parent=parent_id,
        ).execute()

        return self.from_google(self.tasklist, res)


class GoogleList(BaseModel):
    id: str
    title: str
    updated: datetime

    @classmethod
    def list(cls):
        resp = client.tasklists().list().execute()
        
        lists = []
        for item in resp["items"]:
            lists.append(cls(**item))

        return lists

    def tasks(self):
        resp = client.tasks().list(tasklist=self.id).execute()
        if resp.get("items"):
            return [GoogleTask.from_google(self.id, task_res) for task_res in resp["items"]]
        else:
            return []