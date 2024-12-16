# Generated by Django 5.0.4 on 2024-12-16 01:30

import wagtail.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0017_rename_start_date_bookingrecord_arrival_date_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='bookingpage',
            name='calendar_text',
            field=wagtail.fields.RichTextField(blank=True, help_text='Text to display above the vacancy calendar'),
        ),
    ]