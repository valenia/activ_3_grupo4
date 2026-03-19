from fastapi import FastAPI

from app.authentication.router import router as authentication_router
from app.files.router import router as files_router

from app.database import TORTOISE_ORM

app = FastAPI()


@app.get("/healthcheck")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(authentication_router)
app.include_router(files_router, prefix="/files")
