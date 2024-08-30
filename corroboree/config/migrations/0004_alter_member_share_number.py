# Generated by Django 5.0.4 on 2024-08-28 05:10

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('config', '0003_season_max_monthly_simultaneous_rooms'),
    ]

    operations = [
        migrations.AlterField(
            model_name='member',
            name='share_number',
            field=models.IntegerField(primary_key=True, serialize=False, validators=[django.core.validators.MaxValueValidator(50, message='Cannot exceed 50 shares'), django.core.validators.MinValueValidator(0, message='Share number is less than 1')]),
        ),
    ]