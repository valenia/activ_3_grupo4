from fastapi import APIRouter

router = APIRouter()

# Local dictrionary to store users and sessions
users_db = {}        # {email: {"id": int, "password": str, "name": str}}
sessions_db = {}     # {token: {"user_id": int}}
user_id_counter = 1

@router.post("/healthcheck")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/register")
async def register() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/login")
async def login() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/logout")
async def logout() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/introspect")
async def checkToken() -> dict[str, str]:
    return {"status": "ok"}

