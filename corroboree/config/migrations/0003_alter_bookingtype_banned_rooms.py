# Generated by Django 5.0.3 on 2024-04-08 04:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('config', '0002_alter_season_max_monthly_room_weeks'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bookingtype',
            name='banned_rooms',
            field=models.ManyToManyField(blank=True, null=True, to='config.room'),
        ),
    ]
