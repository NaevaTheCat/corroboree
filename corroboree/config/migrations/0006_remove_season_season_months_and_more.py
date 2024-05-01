# Generated by Django 5.0.3 on 2024-04-18 06:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('config', '0005_alter_season_season_months'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='season',
            name='season_months',
        ),
        migrations.AlterField(
            model_name='season',
            name='max_monthly_room_weeks',
            field=models.IntegerField(blank=True, help_text='Leave blank for no limit', null=True),
        ),
    ]