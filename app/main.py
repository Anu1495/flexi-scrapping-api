from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(
    title="Google Sheets Read API",
    description="Read rows from a configured Google Sheet and return them as JSON.",
    version="1.0.0",
)

app.include_router(router, prefix="/api/v1")