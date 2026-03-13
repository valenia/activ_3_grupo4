from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def files_get() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/{id}")
async def files_id_get(id: int) -> dict[str, int]:
    return {"status": id}


@router.post("/{id}")
async def files_id_post(id: str) -> dict[str, str]:
    return {"status": id}


@router.delete("/{id}")
async def files_id_post(id: str) -> dict[str, int]:
    return {"status": id}
