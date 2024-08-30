# Generated by Django 5.0.4 on 2024-08-28 05:32

import corroboree.config.models
import django.db.models.deletion
import wagtail.blocks
import wagtail.fields
import wagtail.snippets.blocks
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('wagtailcore', '0091_remove_revision_submitted_for_moderation'),
    ]

    operations = [
        migrations.CreateModel(
            name='RatesPage',
            fields=[
                ('page_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='wagtailcore.page')),
                ('subheading', models.CharField(max_length=512)),
                ('rates_tables', wagtail.fields.StreamField([('season_rates', wagtail.blocks.ListBlock(wagtail.blocks.StructBlock([('season', wagtail.snippets.blocks.SnippetChooserBlock(corroboree.config.models.Season)), ('rates', wagtail.blocks.ListBlock(wagtail.blocks.StructBlock([('display_name', wagtail.blocks.CharBlock()), ('booking_type', wagtail.snippets.blocks.SnippetChooserBlock(corroboree.config.models.BookingType))])))]))), ('notes', wagtail.blocks.StructBlock([('heading', wagtail.blocks.CharBlock()), ('notes', wagtail.blocks.ListBlock(wagtail.blocks.CharBlock()))]))])),
            ],
            options={
                'abstract': False,
            },
            bases=('wagtailcore.page',),
        ),
    ]
