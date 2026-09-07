from wagtail.models import Page, Site
from wagtail.test.utils import WagtailPageTestCase

from home.factories import HomePageFactory
from corroboree.news.factories import NewsPageFactory, NewsPagePostFactory


class NewsPageTests(WagtailPageTestCase):
    def setUp(self):
        root = Page.objects.get(id=1)
        self.home = HomePageFactory(parent=root)
        # Point the existing default Site at our test home page, so pages
        # under it get resolvable URLs. Wagtail's migrations already create
        # one default Site; only one Site may have is_default_site=True, so
        # we repoint it rather than creating a second one.
        site = Site.objects.get(is_default_site=True)
        site.root_page = self.home
        site.save()

        self.news_page = NewsPageFactory(parent=self.home)

    def test_news_page_renders(self):
        self.assertPageIsRenderable(self.news_page)

    def test_news_page_with_posts_renders(self):
        NewsPagePostFactory(parent=self.news_page)
        self.assertPageIsRenderable(self.news_page)

    def test_context_orders_posts_by_date_descending(self):
        older = NewsPagePostFactory(parent=self.news_page, pub_date="2024-01-01")
        newer = NewsPagePostFactory(parent=self.news_page, pub_date="2025-01-01")

        context = self.news_page.get_context(request=None)

        self.assertEqual(list(context['newspages']), [newer, older])

    def test_news_page_content_matches_news_posts(self):
        post_1 = NewsPagePostFactory(parent=self.news_page)
        post_2 = NewsPagePostFactory(parent=self.news_page, body="<p>Post_2 Body</p>")
        response = self.client.get(self.news_page.url)

        self.assertContains(response, post_1.title)
        self.assertContains(response, post_1.pub_date.strftime("%B %Y"))
        self.assertContains(response, post_1.body)

        self.assertContains(response, post_2.title)
        self.assertContains(response, post_2.pub_date.strftime("%B %Y"))
        self.assertContains(response, post_2.body)