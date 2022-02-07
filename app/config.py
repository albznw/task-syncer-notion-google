import os
import sys
import json
import logging
from dotenv import dotenv_values

settings = None
    
def setup_logger() -> logging.Logger:
    log_formatter = logging.Formatter("[%(levelname)-5.5s]  %(message)s")
    log_handler = logging.StreamHandler(sys.stdout)
    log_handler.setFormatter(log_formatter)

    logger = logging.getLogger("TaskSyncer")
    logger.addHandler(log_handler)
    logger.setLevel(logging.DEBUG)
    return logger

def read_notion_config() -> dict:
    notion_settings_file_name = "notion_settings.json"
    notion_settings_file_path = os.path.join(os.path.dirname(__file__), notion_settings_file_name)
    if not os.path.exists(notion_settings_file_path):
        print(
            f"The file {notion_settings_file_name} is missing from app "
            "directory. You have to run setup.py to configure Notion."
        )
        exit(0)
    
    with open(notion_settings_file_path, "r") as f:
        notion_settings = json.load(f)

    return notion_settings

    
class Settings():
    # Logger
    logger: logging.Logger
    app_name: str = "TaskSyncer Notion-Google"

    # MongoDB
    mongo_db_username: str
    mongo_db_password: str

    # Notion
    notion_secret: str
    notion_task_db: str
    notion_bucket_db: str
    notion_settings: dict

    def __init__(self):
        print("PRODUCTION SETTINGS")
        print("Loading .env")
        env = dotenv_values(".env")

        self.logger = setup_logger()
        self.logger.info("Setting up...")
        self.notion_settings = read_notion_config()
        self.logger.info("Done")


class BaseSettings():
    app_name: str

    # Mongo credentials
    mongo_username: str
    mongo_password: str
    mongo_url: str
    mongo_db: str

    # Notion
    notion_secret: str
    notion_task_db: str
    notion_bucket_db: str

    # Google
    google_default_tasklist: str


class TestSettings():

    def __init__(self):
        print("TEST SETTINGS")
        print("Loading test.env")
        env = dotenv_values("test.env")

        self.app_name = "TaskSyncer Notion-Google (TEST)"

        # Mongo credentials
        self.mongo_username: str = env.get("MONGO_USERNAME")
        self.mongo_password: str = env.get("MONGO_PASSWORD")
        self.mongo_url: str = env.get("MONGO_URL")
        self.mongo_db: str = env.get("MONGO_DB")

        # Notion
        self.notion_secret: str = env.get("NOTION_SECRET")
        self.notion_task_db: str = env.get("NOTION_TASK_DB")
        self.notion_bucket_db: str = env.get("NOTION_BUCKET_DB")

        # Google
        self.google_default_tasklist = env.get("GOOGLE_DEFAULT_TASKLIST")

if os.environ.get("ENV") == "TEST":
    settings = TestSettings()
else:
    settings = Settings()
    