import pytest
from urllib.parse import quote_plus
from pymongo import MongoClient


from app.config import settings

mongo_uri = f"mongodb://{quote_plus(settings.mongo_username)}:{quote_plus(settings.mongo_password)}@{settings.mongo_url}"

@pytest.fixture()
def mongo_fixture():
    print("setup")
    db_client = MongoClient(mongo_uri)
    yield
    print("teardown")
    db_client.drop_database(settings.mongo_db)
