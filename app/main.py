from app.config import settings
from app.syncers import notion as notion_syncer
from app.syncers import google as google_syncer

logger = settings.logger

logger.info("Syncing...")

# First time syncing
notion_syncer.sync(remove_dangling_tasks=False)
# google_syncer.sync(remove_dangling_tasks=False)

while True:
    # notion_syncer.sync()
    google_syncer.sync()

    print("shit")
