from fastapi import FastAPI
from notion_client import Client as NotionClient

from app.config import settings
from app.models import notion

app = FastAPI()
notion_client = NotionClient(auth=settings.notion_secret)


@app.get("/")
async def root():
    return {"message": "Hello World"}