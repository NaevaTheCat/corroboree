# Generated by Django 5.0.4 on 2024-09-03 04:18

import django.db.models.deletion
import wagtail.blocks
import wagtail.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('corroboree', '0002_textpage_body'),
        ('wagtailcore', '0091_remove_revision_submitted_for_moderation'),
    ]

    operations = [
        migrations.CreateModel(
            name='PolicyPage',
            fields=[
                ('page_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='wagtailcore.page')),
                ('date_revised', models.DateField()),
                ('body', wagtail.fields.RichTextField()),
            ],
            options={
                'abstract': False,
            },
            bases=('wagtailcore.page',),
        ),
        migrations.AddField(
            model_name='policiespage',
            name='body',
            field=wagtail.fields.StreamField([('policy', wagtail.blocks.PageChooserBlock(page_type=['corroboree.PolicyPage'])), ('section', wagtail.blocks.StructBlock([('heading', wagtail.blocks.CharBlock(max_length=512)), ('intro_text', wagtail.blocks.RichTextBlock())])), ('policy_with_subpolicies', wagtail.blocks.StructBlock([('policy', wagtail.blocks.PageChooserBlock(page_type=['corroboree.PolicyPage'])), ('sub_policies', wagtail.blocks.ListBlock(wagtail.blocks.PageChooserBlock(page_type=['corroboree.PolicyPage'])))]))], default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='policiespage',
            name='introduction',
            field=wagtail.fields.RichTextField(default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='policiespage',
            name='subheading',
            field=models.CharField(default='', max_length=512),
            preserve_default=False,
        ),
    ]