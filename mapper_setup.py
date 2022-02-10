import json
from os import path
from app.models.notion import NotionStatus
from app.models.google import GoogleStatus
from app.config import settings


FILE_NAME = "status_mapper.json"
FILE_PATH = path.join(path.dirname(__file__), "app", FILE_NAME)

print(
    "The setup helper is made to help you fetch and configure the needed "
    "Notion id's for statuses, labels, buckets, etc.\n"
    "This helper program has to be run manually."
)

print("\nAs for the lists/buckets between Notion and Google. These simply need "
      "to have (exactly) the same name.")

task_database = settings.notion_task_db
if not task_database:
    task_database = input(
        "Enter the Notion database id of your Task database\n"
        "Example: cb8083r6-2845-427d-a195-5bbf2a5e6429\n"
        "> "
    )


print('In notion it\'s possible to have more than "todo" and "done" as a '
      'status. Please map your statuses in Notion to Google statuses')

# Fetch possible Notion statuses
notion_statuses = NotionStatus.list()

print("Possible Notion statuses:")
for index in range(len(notion_statuses)):
    print(f"   {index}. {notion_statuses[index].name} (nid={notion_statuses[index].notion_id})")

print('\nFor each Notion status, enter "d" (Done) and "t" (Todo) as how you '
      'would like them to map to Google')

status_mapping = []
for index in range(len(notion_statuses)):
    while True:
        mapping = input(f'{notion_statuses[index].name} > ')
        
        if mapping == "d":
            google_status = {
                "name": GoogleStatus.done.value,
            }
        elif mapping == "t":
            google_status = {
                "name": GoogleStatus.todo.value,
            }
        else:
            print('You have to enter either "d" or "t"')
            continue
        
        status_mapping.append({
            "google": google_status,
            "notion": notion_statuses[index].dict(include={"notion_id", "name", "color"})
        })
        break

print(f"\nWriting settings to {FILE_PATH}")
with open(FILE_PATH, "w") as f:
    json.dump(status_mapping, f)

print("\nDone with setup.\n\n")
