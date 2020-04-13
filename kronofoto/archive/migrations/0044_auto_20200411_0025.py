# Generated by Django 2.2.10 on 2020-04-11 00:25

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('archive', '0043_auto_20200411_0017'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='collection',
            name='displayed_donors',
        ),
        migrations.RemoveField(
            model_name='collection',
            name='is_published',
        ),
        migrations.RemoveField(
            model_name='collection',
            name='total_photos',
        ),
        migrations.RemoveField(
            model_name='collection',
            name='year_max',
        ),
        migrations.RemoveField(
            model_name='collection',
            name='year_min',
        ),
        migrations.AddField(
            model_name='collection',
            name='owner',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='collection',
            name='visibility',
            field=models.CharField(choices=[('PR', 'Private'), ('UL', 'Unlisted'), ('PU', 'Public')], default='PR', max_length=2),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='scannedphoto',
            name='donor',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='archive.Donor'),
        ),
        migrations.AlterField(
            model_name='collection',
            name='description',
            field=models.TextField(blank=True),
        ),
    ]
