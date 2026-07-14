# Generated manually

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_notification_organization_name_blank'),
    ]

    operations = [
        migrations.CreateModel(
            name='StoredFile',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('original_name', models.CharField(blank=True, max_length=255)),
                ('content_type', models.CharField(default='application/octet-stream', max_length=100)),
                ('size', models.PositiveIntegerField(default=0)),
                ('data', models.BinaryField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Файл в БД',
                'verbose_name_plural': 'Файлы в БД',
            },
        ),
    ]
