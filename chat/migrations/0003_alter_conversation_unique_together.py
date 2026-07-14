# Generated manually

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0002_support_attachments_message_edit'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='conversation',
            unique_together=set(),
        ),
    ]
