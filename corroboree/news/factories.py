import factory
import wagtail_factories
from django.utils import timezone
from corroboree.news.models import NewsPage, NewsPagePost


class NewsPageFactory(wagtail_factories.PageFactory):
    class Meta:
        model = NewsPage
    title = "News"
    slug = "news"


class NewsPagePostFactory(wagtail_factories.PageFactory):
    class Meta:
        model = NewsPagePost
    # Sequence gives each post a unique title/slug automatically,
    # so you never get slug collisions between test cases
    title = factory.Sequence(lambda n: f"Post {n}")
    slug = factory.Sequence(lambda n: f"post-{n}")
    pub_date = factory.LazyFunction(lambda: timezone.now().date())
    body = "<p>Test post body</p>"