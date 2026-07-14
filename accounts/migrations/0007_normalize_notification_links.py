from django.db import migrations


def normalize_all_notification_links(apps, schema_editor):
    Notification = apps.get_model('accounts', 'Notification')
    fixes = {
        '/seller/requests/#offers': '/accounts/my-requests/#offers',
        '/seller/requests/': '/accounts/my-requests/',
        '/seller/requests/#sent': '/seller/requests/#sent',
        '/catalog/looking/#my-requests': '/accounts/my-requests/#offers',
        '/catalog/looking/#my-offers': '/seller/requests/#sent',
    }
    for n in Notification.objects.all():
        link = (n.link or '').strip()
        if link in fixes:
            n.link = fixes[link]
            n.save(update_fields=['link'])
        elif link.startswith('/seller/requests'):
            suffix = '#' + link.split('#', 1)[1] if '#' in link else ''
            n.link = '/accounts/my-requests/' + suffix.replace('/#', '#')
            n.save(update_fields=['link'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_fix_offer_notification_links'),
    ]

    operations = [
        migrations.RunPython(normalize_all_notification_links, migrations.RunPython.noop),
    ]
