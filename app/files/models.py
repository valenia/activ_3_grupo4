from tortoise import fields, models


class StoredFile(models.Model):
    id = fields.IntField(pk=True)
    owner_external_id = fields.IntField()
    filename = fields.CharField(max_length=255)
    description = fields.TextField(null=True)
    mime_type = fields.CharField(max_length=100, null=True)
    content = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "stored_files"
