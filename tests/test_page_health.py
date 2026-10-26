from bs4 import BeautifulSoup

from features.page_health import check_page_health


def test_all_checks_pass_on_a_well_formed_page():
    html = """
    <html><head>
      <title>Apex Dental Clinic - Family Dentistry in Austin</title>
      <meta name="description" content="Apex Dental Clinic offers family and cosmetic dentistry in Austin, TX, with same-day appointments and modern equipment.">
      <meta name="viewport" content="width=device-width, initial-scale=1">
    </head><body>
      <img src="a.jpg" alt="Dental office waiting room">
      <img src="b.jpg" alt="Dentist examining a patient">
    </body></html>
    """
    result = check_page_health(BeautifulSoup(html, "html.parser"), "https://example.com/")
    statuses = {c["id"]: c["status"] for c in result["checks"]}
    assert statuses == {
        "title": "pass",
        "description": "pass",
        "alt_text": "pass",
        "https": "pass",
        "viewport": "pass",
    }
    assert result["passed"] == result["total"] == 5


def test_missing_everything_fails_cleanly():
    html = "<html><head></head><body><img src='a.jpg'></body></html>"
    result = check_page_health(BeautifulSoup(html, "html.parser"), "http://example.com/")
    statuses = {c["id"]: c["status"] for c in result["checks"]}
    assert statuses["title"] == "fail"
    assert statuses["description"] == "fail"
    assert statuses["alt_text"] == "fail"  # 0% of 1 image has alt text
    assert statuses["https"] == "fail"  # plain http
    assert statuses["viewport"] == "fail"
    assert result["passed"] == 0


def test_no_images_counts_as_a_pass_not_a_penalty():
    html = "<html><head><title>x</title></head><body><p>no images here</p></body></html>"
    result = check_page_health(BeautifulSoup(html, "html.parser"), "https://example.com/")
    alt_check = next(c for c in result["checks"] if c["id"] == "alt_text")
    assert alt_check["status"] == "pass"


def test_title_too_long_warns_not_fails():
    html = "<html><head><title>" + ("x" * 100) + "</title></head><body></body></html>"
    result = check_page_health(BeautifulSoup(html, "html.parser"), "https://example.com/")
    title_check = next(c for c in result["checks"] if c["id"] == "title")
    assert title_check["status"] == "warn"
