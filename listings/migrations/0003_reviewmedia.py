from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('listings', '0002_media_and_remove_barcode'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReviewMedia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='reviews/')),
                ('media_type', models.CharField(choices=[('image', 'Фото'), ('video', 'Видео')], default='image', max_length=10)),
                ('sort_order', models.IntegerField(default=0)),
                ('review', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='media', to='listings.review')),
            ],
            options={
                'ordering': ['sort_order'],
            },
        ),
    ]
