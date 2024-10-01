from django.db import models
from django.utils import timezone
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Page


class NewsPage(Page):
    content_panels = Page.content_panels

    parent_page_types = ['home.HomePage']
    subpage_types = ['NewsPagePost']

    # custom context for ordering news posts
    def get_context(self, request):
        context = super().get_context(request)
        newspages = NewsPagePost.objects.live().order_by('-pub_date')
        context['newspages'] = newspages
        return context


class NewsPagePost(Page):
    body = RichTextField()
    pub_date = models.DateField("Post date", default=timezone.now())

    content_panels = Page.content_panels + [
        FieldPanel('pub_date'),
        FieldPanel('body'),
    ]

    parent_page_types = ['NewsPage']
    subpage_types = []
