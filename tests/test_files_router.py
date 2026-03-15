import asyncio
import base64

import pytest
from pypdf import PdfWriter

from app.files import router as files_router


def _create_pdf_base64() -> str:
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    from io import BytesIO

    output = BytesIO()
    writer.write(output)
    return base64.b64encode(output.getvalue()).decode("utf-8")


def setup_function() -> None:
    files_router._files_store.clear()
    files_router._next_file_id = 1


def test_create_and_list_files_for_owner() -> None:
    created = asyncio.run(
        files_router.files_post(
            files_router.FileCreateInput(
                filename="doc.txt",
                description="desc",
                content_type="text/plain",
            ),
            auth="user-a",
        )
    )
    assert created.id == 1

    payload = asyncio.run(files_router.files_get(auth="user-a"))
    assert len(payload) == 1
    assert payload[0].id == 1
    assert payload[0].filename == "doc.txt"
    assert payload[0].has_content is False

    files_for_user_b = asyncio.run(files_router.files_get(auth="user-b"))
    assert files_for_user_b == []


def test_upload_content_and_get_file_detail() -> None:
    created = asyncio.run(
        files_router.files_post(
            files_router.FileCreateInput(filename="payload.bin"),
            auth="token-user-1",
        )
    )
    file_id = created.id

    raw_content = b"hello"
    upload_response = asyncio.run(
        files_router.files_id_post(
            file_id,
            files_router.FileContentInput(
                content_base64=base64.b64encode(raw_content).decode("utf-8")
            ),
            auth="token-user-1",
        )
    )
    assert upload_response["status"] == "ok"

    detail_response = asyncio.run(files_router.files_id_get(file_id, auth="token-user-1"))
    assert detail_response.content_base64 == base64.b64encode(raw_content).decode("utf-8")


def test_delete_file() -> None:
    created = asyncio.run(
        files_router.files_post(
            files_router.FileCreateInput(filename="to-delete.txt"),
            auth="token-user-1",
        )
    )
    file_id = created.id

    delete_response = asyncio.run(files_router.files_id_delete(file_id, auth="token-user-1"))
    assert delete_response["status"] == "deleted"

    with pytest.raises(files_router.HTTPException) as exc:
        asyncio.run(files_router.files_id_get(file_id, auth="token-user-1"))
    assert exc.value.status_code == 404


def test_merge_two_pdf_files() -> None:
    pdf_content = _create_pdf_base64()

    first = asyncio.run(
        files_router.files_post(
            files_router.FileCreateInput(
                filename="first.pdf",
                content_type="application/pdf",
            ),
            auth="token-user-1",
        )
    )
    second = asyncio.run(
        files_router.files_post(
            files_router.FileCreateInput(
                filename="second.pdf",
                content_type="application/pdf",
            ),
            auth="token-user-1",
        )
    )

    first_id = first.id
    second_id = second.id

    asyncio.run(
        files_router.files_id_post(
            first_id,
            files_router.FileContentInput(content_base64=pdf_content),
            auth="token-user-1",
        )
    )
    asyncio.run(
        files_router.files_id_post(
            second_id,
            files_router.FileContentInput(content_base64=pdf_content),
            auth="token-user-1",
        )
    )

    merge_response = asyncio.run(
        files_router.files_merge_post(
            files_router.MergeInput(
                file_id_1=first_id,
                file_id_2=second_id,
                merged_filename="merged.pdf",
            ),
            auth="token-user-1",
        )
    )
    merged_id = merge_response.id

    merged_detail = asyncio.run(files_router.files_id_get(merged_id, auth="token-user-1"))
    assert merged_detail.content_type == "application/pdf"
    assert merged_detail.has_content is True


def test_missing_auth_header_returns_401() -> None:
    with pytest.raises(files_router.HTTPException) as exc:
        asyncio.run(files_router.files_get(auth=None))
    assert exc.value.status_code == 401
