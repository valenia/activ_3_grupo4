from fastapi import APIRouter

router = APIRouter()


@router.post("/healthcheck")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
