from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_normalize_notification_links'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='delivery_address',
            field=models.TextField(blank=True, verbose_name='Адрес доставки'),
        ),
    ]
