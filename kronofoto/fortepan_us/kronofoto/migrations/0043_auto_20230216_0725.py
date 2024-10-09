# Generated by Django 3.2.17 on 2023-02-16 07:25

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('kronofoto', '0042_auto_20230216_0719'),
    ]

    operations = [
        migrations.AddField(
            model_name='donor',
            name='archive',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='kronofoto.archive'),
        ),
        migrations.AddField(
            model_name='photo',
            name='archive',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='kronofoto.archive'),
        ),
    ]