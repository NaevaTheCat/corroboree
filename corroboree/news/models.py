from django.db import models

from wagtail.models import Page
from wagtail.fields import RichTextField
from wagtail.admin.panels import FieldPanel


class NewsPage(Page):
    content_panels = Page.content_panels

    # custom context for ordering news posts
    def get_context(self, request):
        context = super().get_context(request)
        newspages = NewsPagePost.objects.live().order_by('-pub_date')
        context['newspages'] = newspages
        return context


class NewsPagePost(Page):
    body = RichTextField()
    pub_date = models.DateField("Post date")

    content_panels = Page.content_panels + [
        FieldPanel('pub_date'),
        FieldPanel('body'),
    ]
