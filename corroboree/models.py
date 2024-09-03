from django.db import models
from wagtail.admin.panels import FieldPanel
from wagtail.models import Page
from wagtail.fields import StreamField, RichTextField
from wagtail import blocks
from wagtail.snippets.blocks import SnippetChooserBlock
from corroboree.config.models import Season, BookingType


class ContactPage(Page):
    pass


class PolicyPage(Page):
    date_revised = models.DateField()
    body = RichTextField()

    content_panels = Page.content_panels + [
        FieldPanel('date_revised'),
        FieldPanel('body'),
    ]

    parent_page_types = ['PoliciesPage', 'PolicyPage']
    subpage_types = ['PolicyPage']


class SectionBlock(blocks.StructBlock):
    heading = blocks.CharBlock(max_length=512)
    intro_text = blocks.RichTextBlock(required=False)


class PolicyWithSubPoliciesBlock(blocks.StructBlock):
    policy = blocks.PageChooserBlock(page_type=PolicyPage)
    sub_policies = blocks.ListBlock(
        blocks.PageChooserBlock(page_type=PolicyPage),
    )


class PoliciesPage(Page):
    subheading = models.CharField(max_length=512)
    introduction = RichTextField()
    body = StreamField([
        ('policy', blocks.PageChooserBlock(page_type=PolicyPage)),
        ('section', SectionBlock()),
        ('policy_with_subpolicies', PolicyWithSubPoliciesBlock()),
    ], blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('subheading'),
        FieldPanel('introduction'),
        FieldPanel('body'),
    ]

    parent_page_types = ['home.HomePage']
    subpage_types = ['PolicyPage']


class TextPage(Page):
    body = RichTextField()

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]

    parent_page_types = ['home.HomePage']
    subpage_types = []
