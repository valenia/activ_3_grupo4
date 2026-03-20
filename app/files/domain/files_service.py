from app.files.domain.exceptions import (
    FileNotFoundError,
    UnauthorizedFileAccessError,
)
from app.files.persistence.files_repository import FilesRepository


class FilesService:
    def __init__(self, repository: FilesRepository):
        self.repository = repository

    async def list_files(self, owner_external_id: int):
        return await self.repository.list_by_owner(owner_external_id)

    async def create_file(
        self,
        owner_external_id: int,
        filename: str,
        description: str | None,
        mime_type: str | None,
    ):
        return await self.repository.create_file(
            owner_external_id=owner_external_id,
            filename=filename,
            description=description,
            mime_type=mime_type,
        )

    async def get_file(self, owner_external_id: int, file_id: int):
        file_obj = await self.repository.get_file_by_id(file_id)

        if not file_obj:
            raise FileNotFoundError()

        if file_obj.owner_external_id != owner_external_id:
            raise UnauthorizedFileAccessError()

        return file_obj

    async def upload_content(
        self,
        owner_external_id: int,
        file_id: int,
        content: str,
    ):
        file_obj = await self.get_file(owner_external_id, file_id)
        file_obj.content = content
        await self.repository.save(file_obj)
        return file_obj

    async def delete_file(self, owner_external_id: int, file_id: int):
        file_obj = await self.get_file(owner_external_id, file_id)
        await self.repository.delete(file_obj)