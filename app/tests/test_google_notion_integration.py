from app.models.mongo import NotionTaskRepository
from app.models.notion import NotionTasks
from app.syncers.google import GoogleSyncer

from app.tests.fixtures import mongo_fixture

def test_syncer(mongo_fixture):
    syncer = GoogleSyncer()
    pass
    syncer.sync()
    pass
    syncer.sync()