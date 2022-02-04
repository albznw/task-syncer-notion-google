from os import path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/tasks']

creds = None
# The file token.json stores the user's access and refresh tokens, and is
# created automatically when the authorization flow completes for the first
# time.

dirname = path.dirname(__file__)
credentials_path = path.join(dirname, "app/google_api_credentials.json")
token_path = path.join(dirname, "token.json")
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