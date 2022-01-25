from pydantic import BaseSettings


class Settings(BaseSettings):
    app_name: str = "TaskSyncer Notion-Google"
    notion_secret: str
    noition_task_db: str
    # google_secret: str

    class Config:
        env_file = ".env"


settings = Settings()

# if settings.notion_secret == "" or settings.google_secret == "":
    # raise EnvironmentError("You need to specify tokens")