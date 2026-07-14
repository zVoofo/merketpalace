import mimetypes
import uuid
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import Storage


class DatabaseStorage(Storage):
    """Файлы в PostgreSQL — работает на Render без облака и сервисных аккаунтов."""

    def _open(self, name, mode='rb'):
        from accounts.models import StoredFile
        try:
            uuid.UUID(str(name))
        except (ValueError, TypeError, AttributeError):
            raise FileNotFoundError(name)
        obj = StoredFile.objects.get(pk=name)
        return ContentFile(obj.data, name=obj.original_name)

    def get_available_name(self, name, max_length=None):
        return str(uuid.uuid4())

    def _save(self, name, content, max_length=None):
        from accounts.models import StoredFile
        data = content.read()
        max_size = getattr(settings, 'MAX_DB_FILE_SIZE', 50 * 1024 * 1024)
        if len(data) > max_size:
            raise ValueError(f'Файл больше {max_size // (1024 * 1024)} МБ')
        original = getattr(content, 'name', name) or 'file'
        ct = getattr(content, 'content_type', None) or mimetypes.guess_type(original)[0] or 'application/octet-stream'
        try:
            file_id = uuid.UUID(str(name))
        except (ValueError, TypeError, AttributeError):
            file_id = uuid.uuid4()
        StoredFile.objects.create(
            id=file_id,
            original_name=original[:255],
            content_type=ct[:100],
            size=len(data),
            data=data,
        )
        return str(file_id)

    def delete(self, name):
        from accounts.models import StoredFile
        try:
            uuid.UUID(str(name))
        except (ValueError, TypeError, AttributeError):
            return
        StoredFile.objects.filter(pk=name).delete()

    def exists(self, name):
        from accounts.models import StoredFile
        try:
            uuid.UUID(str(name))
        except (ValueError, TypeError, AttributeError):
            return False
        return StoredFile.objects.filter(pk=name).exists()

    def url(self, name):
        if not name:
            return ''
        return f'/files/{name}/'

    def size(self, name):
        from accounts.models import StoredFile
        try:
            uuid.UUID(str(name))
        except (ValueError, TypeError, AttributeError):
            return 0
        obj = StoredFile.objects.filter(pk=name).first()
        return obj.size if obj else 0
