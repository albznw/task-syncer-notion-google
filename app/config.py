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

def read_status_mapper() -> dict:
    status_mapper_file_name = "status_mapper.json"
    status_mapper_file_path = os.path.join(os.path.dirname(__file__), status_mapper_file_name)
    if not os.path.exists(status_mapper_file_path):
        print(
            f"The file {status_mapper_file_name} is missing from app "
            "directory. You have to run setup.py to configure Notion."
        )
        exit(0)
    
    with open(status_mapper_file_path, "r") as f:
        status_mapper = json.load(f)

    return status_mapper


class BaseSettings():
    # Logger
    logger: logging.Logger
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

    # Mapper
    status_mapper: dict


class Settings(BaseSettings):
    def __init__(self):
        print("PRODCUTION SETTINGS")
        print("Loading .env")
        env = dotenv_values(".env")

        self.logger = setup_logger()
        self.logger.info("Setting up production environment...")
        self.app_name = "TaskSyncer Notion-Google"

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

        # Mapper
        self.status_mapper = read_status_mapper()
        
        self.logger.info("Done")


class TestSettings(BaseSettings):

    def __init__(self):
        print("TEST SETTINGS")
        print("Loading test.env")
        env = dotenv_values("test.env")

        self.logger = setup_logger()
        self.logger.info("Setting up test environment...")
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

        # Mapper
        self.status_mapper = read_status_mapper()
        
        self.logger.info("Done")

if os.environ.get("ENV") == "TEST":
    settings = TestSettings()
else:
    settings = Settings()
    