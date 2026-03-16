from __future__ import annotations

import base64
from datetime import datetime, timezone
from io import BytesIO
from typing import Any

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field
from pypdf import PdfReader, PdfWriter

router = APIRouter(tags=["files"])

# Local dictrionary to store theoretical files
_files_store: dict[int, dict[str, Any]] = {}
_next_file_id = 1

class FileCreateInput(BaseModel):
    filename: str = Field(..., min_length=1, description="Visible filename for the file")
    description: str | None = Field(default=None, description="Optional file description")
    content_type: str | None = Field(default=None, description="MIME type, e.g. application/pdf")


class FileContentInput(BaseModel):
    content_base64: str = Field(
        ...,
        min_length=1,
        description="File content encoded in base64",
    )


class MergeInput(BaseModel):
    file_id_1: int = Field(..., description="First PDF file id")
    file_id_2: int = Field(..., description="Second PDF file id")
    merged_filename: str = Field(default="merged.pdf", min_length=1)
    description: str | None = None


class FileSummary(BaseModel):
    id: int
    filename: str
    description: str | None
    content_type: str | None
    has_content: bool
    owner_external_id: str
    created_at: str
    updated_at: str


class FileDetail(FileSummary):
    content_base64: str | None = None


class FileIdResponse(BaseModel):
    id: int


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_file_id() -> int:
    global _next_file_id
    file_id = _next_file_id
    _next_file_id += 1
    return file_id


def _file_to_summary(file_data: dict[str, Any]) -> FileSummary:
    return FileSummary(
        id=file_data["id"],
        filename=file_data["filename"],
        description=file_data["description"],
        content_type=file_data["content_type"],
        has_content=file_data["content_base64"] is not None,
        owner_external_id=file_data["owner_external_id"],
        created_at=file_data["created_at"],
        updated_at=file_data["updated_at"],
    )


def _decode_base64(content_base64: str) -> bytes:
    try:
        return base64.b64decode(content_base64, validate=True)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid base64 payload",
        ) from exc


def _resolve_external_user_id(token: str) -> str:
    """
    If authentication exposes a session dictionary, token validity is checked there.
    Otherwise, token is used as the external user id to keep this module standalone.
    """
    from app.authentication import router as auth_router

    found_session_store = False
    for attribute_name in (
        "SESSIONS",
        "SESSION_STORE",
        "ACTIVE_SESSIONS",
        "TOKEN_TO_USER",
        "TOKENS",
    ):
        session_store = getattr(auth_router, attribute_name, None)
        if not isinstance(session_store, dict):
            continue

        found_session_store = True
        if token not in session_store:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        session_value = session_store[token]
        if isinstance(session_value, dict):
            for user_key in ("external_id", "user_id", "id", "username", "email"):
                if session_value.get(user_key) is not None:
                    return str(session_value[user_key])
        return str(session_value)

    if found_session_store:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    return token


def _authenticated_user_id(auth: str | None) -> str:
    if not auth:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Auth header",
        )
    return _resolve_external_user_id(auth)


def _get_owned_file(file_id: int, owner_external_id: str) -> dict[str, Any]:
    stored_file = _files_store.get(file_id)
    if stored_file is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    if stored_file["owner_external_id"] != owner_external_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return stored_file


@router.get(
    "", 
    response_model=list[FileSummary], 
    summary="List files",
    description="""
    Retrieves all files belonging to the authenticated user.
    
    Features:
    - Returns only files owned by the user (filtered by token)
    - Files are ordered by ID
    - Includes basic metadata without content
    
    Required headers:
    - Auth: Session token obtained from login
    
    Response:
    List of files with summary information (no content)
    """,
    responses={
        200: {
            "description": "List of user files",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 1,
                            "filename": "document.pdf",
                            "description": "My document",
                            "content_type": "application/pdf",
                            "has_content": True,
                            "owner_external_id": "user123",
                            "created_at": "2026-03-15T10:00:00Z",
                            "updated_at": "2026-03-15T10:00:00Z"
                        }
                    ]
                }
            }
        },
        401: {
            "description": "Invalid or missing token",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid token"}
                }
            }
        }
    })
async def files_get(auth: str | None = Header(default=None, alias="Auth")) -> list[FileSummary]:
    owner_external_id = _authenticated_user_id(auth)
    user_files = [
        _file_to_summary(file_data)
        for file_data in sorted(_files_store.values(), key=lambda item: item["id"])
        if file_data["owner_external_id"] == owner_external_id
    ]
    return user_files


@router.post(
    "",
    response_model=FileIdResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create file metadata",
    description="""
    Creates a new file entry in the system (metadata only).
    
    Two-step process:
    1. This endpoint creates the file record (without content)
    2. Then use `POST /files/{id}` to upload the content
    
    Required headers:
    - Auth: Session token obtained from login
    
    Input fields:
    - `filename`: Visible filename (required)
    - `description`: Optional description
    - `content_type`: MIME type (e.g., application/pdf)
    
    Response:
    ID of the created file (use this to upload content later)
    """,
    responses={
        201: {
            "description": "File created successfully",
            "content": {
                "application/json": {
                    "example": {"id": 42}
                }
            }
        },
        401: {
            "description": "Invalid token",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid token"}
                }
            }
        },
        422: {
            "description": "Invalid input data",
            "content": {
                "application/json": {
                    "example": {"detail": "filename must have at least 1 character"}
                }
            }
        }
    }
)
async def files_post(
    payload: FileCreateInput,
    auth: str | None = Header(default=None, alias="Auth"),
) -> FileIdResponse:
    owner_external_id = _authenticated_user_id(auth)
    file_id = _new_file_id()
    now = _utc_now_iso()
    _files_store[file_id] = {
        "id": file_id,
        "filename": payload.filename,
        "description": payload.description,
        "content_type": payload.content_type,
        "owner_external_id": owner_external_id,
        "content_base64": None,
        "created_at": now,
        "updated_at": now,
    }
    return FileIdResponse(id=file_id)


@router.post(
    "/merge",
    response_model=FileIdResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Merge two PDF files",
    description="""
    Merges two PDF files into a new one.
    
    Requirements:
    - Both files must exist and belong to the user
    - Both files must have content uploaded
    - Both files must be valid PDFs
    
    Required headers:
    - Auth: Session token obtained from login
    
    Process:
    1. Validates that both files exist and are PDFs
    2. Merges pages in order (first file_id_1, then file_id_2)
    3. Creates a new file with the result
    
    Response:
    ID of the newly merged file
    """,
    responses={
        201: {
            "description": "Files merged successfully",
            "content": {
                "application/json": {
                    "example": {"id": 43}
                }
            }
        },
        401: {
            "description": "Invalid token",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid token"}
                }
            }
        },
        403: {
            "description": "Access denied",
            "content": {
                "application/json": {
                    "example": {"detail": "Access denied"}
                }
            }
        },
        404: {
            "description": "File not found",
            "content": {
                "application/json": {
                    "example": {"detail": "File not found"}
                }
            }
        },
        409: {
            "description": "Files without content",
            "content": {
                "application/json": {
                    "example": {"detail": "Both files must have content before merge"}
                }
            }
        },
        422: {
            "description": "Invalid PDF",
            "content": {
                "application/json": {
                    "example": {"detail": "Both file contents must be valid PDF documents"}
                }
            }
        }
    }
)
async def files_merge_post(
    payload: MergeInput,
    auth: str | None = Header(default=None, alias="Auth"),
) -> FileIdResponse:
    owner_external_id = _authenticated_user_id(auth)
    first_file = _get_owned_file(payload.file_id_1, owner_external_id)
    second_file = _get_owned_file(payload.file_id_2, owner_external_id)

    if first_file["content_base64"] is None or second_file["content_base64"] is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Both files must have content before merge",
        )

    first_content = _decode_base64(first_file["content_base64"])
    second_content = _decode_base64(second_file["content_base64"])

    try:
        writer = PdfWriter()
        for page in PdfReader(BytesIO(first_content)).pages:
            writer.add_page(page)
        for page in PdfReader(BytesIO(second_content)).pages:
            writer.add_page(page)

        output = BytesIO()
        writer.write(output)
        merged_content = output.getvalue()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Both file contents must be valid PDF documents",
        ) from exc

    file_id = _new_file_id()
    now = _utc_now_iso()
    _files_store[file_id] = {
        "id": file_id,
        "filename": payload.merged_filename,
        "description": payload.description,
        "content_type": "application/pdf",
        "owner_external_id": owner_external_id,
        "content_base64": base64.b64encode(merged_content).decode("utf-8"),
        "created_at": now,
        "updated_at": now,
    }
    return FileIdResponse(id=file_id)


@router.get(
    "/{id}", 
    response_model=FileDetail, 
    summary="Get file detail",
    description="""
    Retrieves complete file information, including content.
    
    Required headers:
    - Auth: Session token obtained from login
    
    Parameters:
    - `id`: ID of the file to retrieve
    
    Response:
    - Complete file metadata
    - Content in base64 (if exists)
    """,
    responses={
        200: {
            "description": "File found",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "filename": "document.pdf",
                        "description": "My document",
                        "content_type": "application/pdf",
                        "has_content": True,
                        "owner_external_id": "user123",
                        "created_at": "2026-03-15T10:00:00Z",
                        "updated_at": "2026-03-15T10:00:00Z",
                        "content_base64": "JVBERi0xLjQKJcOkw7zD..."
                    }
                }
            }
        },
        401: {
            "description": "Invalid token",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid token"}
                }
            }
        },
        403: {
            "description": "Access denied",
            "content": {
                "application/json": {
                    "example": {"detail": "Access denied"}
                }
            }
        },
        404: {
            "description": "File not found",
            "content": {
                "application/json": {
                    "example": {"detail": "File not found"}
                }
            }
        }
    }
)
async def files_id_get(
    id: int,
    auth: str | None = Header(default=None, alias="Auth"),
) -> FileDetail:
    owner_external_id = _authenticated_user_id(auth)
    file_data = _get_owned_file(id, owner_external_id)

    summary = _file_to_summary(file_data)
    return FileDetail(**summary.model_dump(), content_base64=file_data["content_base64"])


@router.post(
    "/{id}", 
    status_code=status.HTTP_200_OK, 
    summary="Upload file content",
    description="""
    Uploads content for an existing file.
    
    Required headers:
    - Auth: Session token obtained from login
    
    Parameters:
    - `id`: ID of the file to upload content to
    
    Request body:
    - `content_base64`: File content encoded in base64
    
    Special behavior:
    - If the file has no `content_type` defined and the content starts with %PDF,
      it automatically assigns `application/pdf`
    
    Response:
    Success confirmation
    """,
    responses={
        200: {
            "description": "Content uploaded successfully",
            "content": {
                "application/json": {
                    "example": {"status": "ok"}
                }
            }
        },
        401: {
            "description": "Invalid token",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid token"}
                }
            }
        },
        403: {
            "description": "Access denied",
            "content": {
                "application/json": {
                    "example": {"detail": "Access denied"}
                }
            }
        },
        404: {
            "description": "File not found",
            "content": {
                "application/json": {
                    "example": {"detail": "File not found"}
                }
            }
        },
        422: {
            "description": "Invalid base64",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid base64 payload"}
                }
            }
        }
    }
)
async def files_id_post(
    id: int,
    payload: FileContentInput,
    auth: str | None = Header(default=None, alias="Auth"),
) -> dict[str, str]:
    owner_external_id = _authenticated_user_id(auth)
    file_data = _get_owned_file(id, owner_external_id)

    raw_content = _decode_base64(payload.content_base64)
    file_data["content_base64"] = base64.b64encode(raw_content).decode("utf-8")

    if file_data["content_type"] is None and raw_content.startswith(b"%PDF"):
        file_data["content_type"] = "application/pdf"
    file_data["updated_at"] = _utc_now_iso()
    return {"status": "ok"}


@router.delete(
    "/{id}", 
    status_code=status.HTTP_200_OK, 
    summary="Delete file",
    description="""
    Permanently deletes a file.
    
    Required headers:
    - Auth: Session token obtained from login
    
    Parameters:
    - `id`: ID of the file to delete
    
    Important:
    This operation is irreversible. The file is completely removed from the system.
    
    Response:
    Deletion confirmation
    """,
    responses={
        200: {
            "description": "File deleted",
            "content": {
                "application/json": {
                    "example": {"status": "deleted"}
                }
            }
        },
        401: {
            "description": "Invalid token",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid token"}
                }
            }
        },
        403: {
            "description": "Access denied",
            "content": {
                "application/json": {
                    "example": {"detail": "Access denied"}
                }
            }
        },
        404: {
            "description": "File not found",
            "content": {
                "application/json": {
                    "example": {"detail": "File not found"}
                }
            }
        }
    }
)
async def files_id_delete(
    id: int,
    auth: str | None = Header(default=None, alias="Auth"),
) -> dict[str, str]:
    owner_external_id = _authenticated_user_id(auth)
    _get_owned_file(id, owner_external_id)
    del _files_store[id]
    return {"status": "deleted"}
