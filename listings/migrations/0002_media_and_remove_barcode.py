# Generated manually

from django.db import migrations, models


def copy_image_to_file(apps, schema_editor):
    ListingImage = apps.get_model('listings', 'ListingImage')
    for img in ListingImage.objects.all():
        if hasattr(img, 'image') and img.image and not img.file:
            img.file = img.image
            img.media_type = 'image'
            img.save(update_fields=['file', 'media_type'])


class Migration(migrations.Migration):

    dependencies = [
        ('listings', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='listingimage',
            name='file',
            field=models.FileField(blank=True, null=True, upload_to='listings/'),
        ),
        migrations.AddField(
            model_name='listingimage',
            name='media_type',
            field=models.CharField(choices=[('image', 'Фото'), ('video', 'Видео')], default='image', max_length=10),
        ),
        migrations.RunPython(copy_image_to_file, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='listingimage',
            name='image',
        ),
        migrations.RemoveField(
            model_name='listingimage',
            name='is_video',
        ),
        migrations.AlterField(
            model_name='listingimage',
            name='file',
            field=models.FileField(upload_to='listings/'),
        ),
        migrations.RemoveField(
            model_name='listing',
            name='barcode',
        ),
    ]
