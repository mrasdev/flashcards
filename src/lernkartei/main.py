from contextlib import asynccontextmanager

from fastapi import FastAPI

from lernkartei.db import init_db
from lernkartei.routers import api


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Lernkartei", lifespan=lifespan)
app.include_router(api.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
