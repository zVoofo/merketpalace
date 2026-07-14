from django.db import migrations


def fix_offer_notification_links(apps, schema_editor):
    Notification = apps.get_model('accounts', 'Notification')
    Notification.objects.filter(link='/seller/requests/#offers').update(
        link='/accounts/my-requests/#offers',
    )
    Notification.objects.filter(link='/seller/requests/').update(
        link='/accounts/my-requests/',
    )


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_storedfile'),
    ]

    operations = [
        migrations.RunPython(fix_offer_notification_links, migrations.RunPython.noop),
    ]
