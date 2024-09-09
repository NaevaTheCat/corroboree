from django.db import models
from wagtail.admin.panels import FieldPanel
from wagtail.models import Page
from wagtail.fields import StreamField, RichTextField
from wagtail import blocks
from wagtail.snippets.blocks import SnippetChooserBlock
from corroboree.config.models import Member


class BoardContactBlock(blocks.StructBlock):
    member = SnippetChooserBlock(Member)
    position = blocks.CharBlock(max_length=128, help_text='Position on board')
    contact_phone = blocks.CharBlock(max_length=14, help_text='Phone number as a string')


class ResponsibilityBlock(blocks.StructBlock):
    title = blocks.CharBlock(max_length=128, help_text='Title of Responsibility')
    member = SnippetChooserBlock(Member)
    contact_phone = blocks.CharBlock(max_length=14, help_text='Phone number as a string')


class ContactPage(Page):
    body = StreamField([
        ('heading', blocks.CharBlock(max_length=128, help_text='A heading within the page')),
        ('board_contacts', blocks.ListBlock(BoardContactBlock())),
        ('responsibility', ResponsibilityBlock())
    ], block_counts={
        'board_contacts': {'min_num': 1, 'max_num': 1},
    })

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]

    parent_page_types = ['home.HomePage']
    subpage_types = []


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
    heading = blocks.CharBlock(max_length=512, help_text='A section subheading to divide kinds of policies')
    intro_text = blocks.RichTextBlock(required=False, help_text='Optional introductory text for the section')


class PolicyWithSubPoliciesBlock(blocks.StructBlock):
    policy = blocks.PageChooserBlock(page_type=PolicyPage, help_text='Choose a child page which is a policy')
    sub_policies = blocks.ListBlock(
        blocks.PageChooserBlock(page_type=PolicyPage, help_text='Choose child pages of the above policy page as subpolicies'),
    )


class PoliciesPage(Page):
    subheading = models.CharField(max_length=512)
    introduction = RichTextField(blank=True)
    body = StreamField([
        ('policy', blocks.PageChooserBlock(page_type=PolicyPage, help_text='Choose a child page which is a policy')),
        ('section', SectionBlock()),
        ('policy_with_subpolicies', PolicyWithSubPoliciesBlock()),
    ], blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('subheading', help_text='Subheading for page. Displayed before policies'),
        FieldPanel('introduction', help_text='Optional Introductory text for page'),
        FieldPanel('body', help_text='Policies are displayed as links to child pages of this page. Create the child '
                                     'pages prior to configuring'),
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
