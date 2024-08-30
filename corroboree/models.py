from django.db import models
from wagtail.admin.panels import FieldPanel
from wagtail.models import Page
from wagtail.fields import StreamField, RichTextField
from wagtail import blocks
from wagtail.snippets.blocks import SnippetChooserBlock
from corroboree.config.models import Season, BookingType

class ContactPage(Page):
    pass

class PoliciesPage(Page):
    pass

class TextPage(Page):
    body = RichTextField()

    content_panels = [
        FieldPanel('body'),
    ]


