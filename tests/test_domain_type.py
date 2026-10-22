from pipeline.build_dataset import classify_domain_type


def test_social_domain():
    assert classify_domain_type("www.facebook.com") == "social"
    assert classify_domain_type("instagram.com") == "social"


def test_directory_domain():
    assert classify_domain_type("www.yelp.com") == "directory_aggregator"
    assert classify_domain_type("justdial.com") == "directory_aggregator"


def test_indian_local_business_directories_are_classified_as_directory_aggregator():
    """Regression test for the DIRECTORY_DOMAINS expansion added for the
    200-query Indian local-business dataset — these are exactly the
    citation targets the model's domain_type feature depends on."""
    indian_directories = [
        "www.magicpin.in", "magicpin.com", "yappe.in", "whatclinic.com",
        "docindia.org", "drlogy.com", "clinicspots.com", "credihealth.com",
        "apollo247.com", "bajajfinservhealth.in", "quickerala.com",
        "discover.lyfskills.com", "yellowpages-uae.com", "threebestrated.in",
        "wanderlog.com",
    ]
    for domain in indian_directories:
        assert classify_domain_type(domain) == "directory_aggregator", (
            f"{domain} should be classified as directory_aggregator"
        )


def test_directory_domain_matches_subdomains_too():
    """DIRECTORY_DOMAINS uses endswith matching, so a subdomain of a listed
    directory domain must still classify as directory_aggregator."""
    assert classify_domain_type("reviews.drlogy.com") == "directory_aggregator"


def test_news_blog_domain():
    assert classify_domain_type("example-news.com") == "news_blog"
    assert classify_domain_type("myblog.example.com") == "news_blog"


def test_default_business_site():
    assert classify_domain_type("apexdental.com") == "business_site"
