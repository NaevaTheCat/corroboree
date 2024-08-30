from django.db import models
from wagtail.admin.panels import FieldPanel
from wagtail.models import Page
from wagtail.fields import StreamField
from wagtail import blocks
from wagtail.snippets.blocks import SnippetChooserBlock
from corroboree.config.models import Season, BookingType


class SeasonRatesBlock(blocks.StructBlock):
    season = SnippetChooserBlock(Season)
    rates = blocks.ListBlock(blocks.StructBlock([
        ('display_name', blocks.CharBlock()),
        ('booking_type', SnippetChooserBlock(BookingType))
        ]))

    class Meta:
        icon = 'table'


class NotesBlock(blocks.StructBlock):
    heading = blocks.CharBlock()
    notes = blocks.ListBlock(blocks.CharBlock())

    class Meta:
        icon = 'clipboard-list'


class RatesPage(Page):
    subheading = models.CharField(max_length=512)
    rates_tables = StreamField([
        ('season_rates', blocks.ListBlock(SeasonRatesBlock())),
        ('notes', NotesBlock())
    ])

    content_panels = Page.content_panels + [
        FieldPanel('subheading'),
        FieldPanel('rates_tables'),
    ]
