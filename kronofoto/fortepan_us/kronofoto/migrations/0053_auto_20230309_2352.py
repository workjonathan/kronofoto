# Generated by Django 3.2.17 on 2023-03-09 23:52

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('kronofoto', '0052_connecticutrecord_year'),
    ]

    operations = [
        migrations.AddField(
            model_name='connecticutrecord',
            name='cleaned_year',
            field=models.IntegerField(null=True),
        ),
        migrations.AlterField(
            model_name='connecticutrecord',
            name='photo',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='kronofoto.photo'),
        ),
    ]
