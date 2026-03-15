import uuid
from typing import Optional

from fastapi import APIRouter, Body, Header, HTTPException
from pydantic import BaseModel

router = APIRouter(tags=["Authentication"])


class RegisterInput(BaseModel):
    username: str
    email: str
    address: Optional[str] = None
    password: str


class UserBO(BaseModel):
    username: str
    email: str
    address: Optional[str] = None
    hashed_password: str


class LoginInput(BaseModel):
    email: str
    password: str


class IntrospectOutput(BaseModel):
    username: str
    email: str
    address: Optional[str] = None


# Local dictionary to store users and sessions
users_db: dict[str, UserBO] = {}
sessions_db: dict[str, str] = {}


def hash_pass(password: str) -> str:
    # Simulación de hash. En un entorno real no se almacenaría la contraseña en texto plano.
    return password


@router.get("/healthcheck")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/register")
async def register(input: RegisterInput = Body()) -> dict[str, str]:
    inner_object = UserBO(
        username=input.username,
        email=input.email,
        address=input.address,
        hashed_password=hash_pass(input.password),
    )

    if inner_object.email not in users_db:
        users_db[inner_object.email] = inner_object
    else:
        raise HTTPException(status_code=409, detail="Email already registered")

    return {"status": "ok"}


@router.post("/login")
async def login(input: LoginInput = Body()) -> dict[str, str]:
    if input.email not in users_db:
        raise HTTPException(status_code=404, detail="Email not registered")

    if hash_pass(input.password) != users_db[input.email].hashed_password:
        raise HTTPException(status_code=401, detail="Incorrect password")

    token = str(uuid.uuid4())
    while token in sessions_db:
        token = str(uuid.uuid4())
    sessions_db[token] = input.email
    return {"auth": token}


@router.post("/logout")
async def logout(auth: str = Header()) -> dict[str, str]:
    if auth not in sessions_db:
        raise HTTPException(status_code=401, detail="Incorrect Token")

    del sessions_db[auth]
    return {"status": "ok"}


@router.get("/introspect")
async def checkToken(auth: str = Header()) -> IntrospectOutput:
    if auth not in sessions_db:
        raise HTTPException(status_code=401, detail="Incorrect Token")

    current_email = sessions_db[auth]
    current_user = users_db[current_email]

    return IntrospectOutput(
        username=current_user.username, email=current_email, address=current_user.address
    )
