from pipeline.build_dataset import classify_domain_type


def test_social_domain():
    assert classify_domain_type("www.facebook.com") == "social"
    assert classify_domain_type("instagram.com") == "social"


def test_directory_domain():
    assert classify_domain_type("www.yelp.com") == "directory_aggregator"
    assert classify_domain_type("justdial.com") == "directory_aggregator"


def test_news_blog_domain():
    assert classify_domain_type("example-news.com") == "news_blog"
    assert classify_domain_type("myblog.example.com") == "news_blog"


def test_default_business_site():
    assert classify_domain_type("apexdental.com") == "business_site"
