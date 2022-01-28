from pydantic import BaseSettings

class Settings(BaseSettings):
    app_name: str = "TaskSyncer Notion-Google"
    notion_secret: str
    notion_task_db: str
    notion_bucket_db: str
    mongo_db_username: str
    mongo_db_password: str

    class Config:
        env_file = ".env"


settings = Settings()
