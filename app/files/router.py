from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.files.domain.files_service import FilesService
from app.files.persistence.files_repository import FilesRepository
from app.files.domain.exceptions import FileNotFoundError, UnauthorizedFileAccessError

router = APIRouter()
repository = FilesRepository()
service = FilesService(repository)

class FileCreateInput(BaseModel):
    filename: str
    description: str | None = None
    content_type: str | None = None

class FileContentInput(BaseModel):
    content_base64: str

class MergeInput(BaseModel):
    file_id_1: int
    file_id_2: int
    merged_filename: str

class FileDetailDesc(BaseModel):
    id: int
    filename: str
    has_content: bool
    content_type: str | None = None
    content_base64: str | None = None

def get_user_id(auth: str | None) -> int:
    if not auth:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        # Mock auth token to user_id parsing for tests
        return hash(auth) % 10000 
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.post("")
async def files_post(input: FileCreateInput, auth: str | None = Header(None)):
    user_id = get_user_id(auth)
    file_obj = await service.create_file(user_id, input.filename, input.description, input.content_type)
    return file_obj

@router.get("")
async def files_get(auth: str | None = Header(None)):
    user_id = get_user_id(auth)
    items = await service.list_files(user_id)
    return [FileDetailDesc(
        id=i.id,
        filename=i.filename,
        has_content=bool(i.content),
        content_type=i.mime_type
    ) for i in items]

@router.post("/{file_id}")
async def files_id_post(file_id: int, input: FileContentInput, auth: str | None = Header(None)):
    user_id = get_user_id(auth)
    try:
        await service.upload_content(user_id, file_id, input.content_base64)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except UnauthorizedFileAccessError:
        raise HTTPException(status_code=403, detail="Unauthorized")
    return {"status": "ok"}

@router.get("/{file_id}")
async def files_id_get(file_id: int, auth: str | None = Header(None)):
    user_id = get_user_id(auth)
    try:
        file_obj = await service.get_file(user_id, file_id)
        return FileDetailDesc(
            id=file_obj.id,
            filename=file_obj.filename,
            has_content=bool(file_obj.content),
            content_type=file_obj.mime_type,
            content_base64=file_obj.content
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Not found")
    except UnauthorizedFileAccessError:
        raise HTTPException(status_code=403, detail="Forbidden")

@router.delete("/{file_id}")
async def files_id_delete(file_id: int, auth: str | None = Header(None)):
    user_id = get_user_id(auth)
    try:
        await service.delete_file(user_id, file_id)
        return {"status": "deleted"}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Not found")
    except UnauthorizedFileAccessError:
        raise HTTPException(status_code=403, detail="Forbidden")

@router.post("/merge")
async def files_merge_post(input: MergeInput, auth: str | None = Header(None)):
    user_id = get_user_id(auth)
    try:
        new_file = await service.merge_files(user_id, [input.file_id_1, input.file_id_2], input.merged_filename, None)
        return new_file
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Not found")
    except UnauthorizedFileAccessError:
        raise HTTPException(status_code=403, detail="Forbidden")
