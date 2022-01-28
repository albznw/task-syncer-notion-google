from time import sleep
from app.sync import notion_to_google_sync, google_to_notion_sync, purge_tasks_google, purge_tasks_notion

if __name__ == "__main__":
    print("Syncing...")
    google_to_notion_sync()
    google_to_notion_sync()
    purge_tasks_notion()
    notion_to_google_sync()
    notion_to_google_sync()
    purge_tasks_google()

sleep(60)
exit(0)
