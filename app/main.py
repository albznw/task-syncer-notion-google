from time import sleep
from app.syncers.google import GoogleSyncer
from app.syncers.notion import NotionSyncer
from app.config import settings

logger = settings.logger

sleep_time = 60

# First time syncing
notion_syncer = NotionSyncer()
google_syncer = GoogleSyncer()

while True:
    notion_syncer.sync()
    google_syncer.sync()
    logger.info(f"Sleeping for {sleep_time} seconds")
    sleep(sleep_time)