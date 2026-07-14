# Generated manually

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0002_searchrequest_matched_listing_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='searchrequest',
            name='matched_seller',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='search_offers_sent', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='searchrequest',
            name='response_seen',
            field=models.BooleanField(default=False),
        ),
    ]
