import scrapy
import os
import re
from urllib.parse import urlparse
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule

class NeptuneSpider(CrawlSpider):
    """
    Neptune Search web crawler.
    Seeds from a list of URLs, follows links, extracts page content,
    and sends it to the Neptune Search API for indexing.

    Run locally:
        scrapy crawl neptune -a seeds="https://en.wikipedia.org/wiki/Neptune" -a max_pages=200

    Run via GitHub Actions: see .github/workflows/crawler.yml
    """
    name = "neptune"

    # Follow most links but skip binary files, ads, tracking, login pages
    rules = (
        Rule(
            LinkExtractor(
                deny_extensions=["pdf","jpg","jpeg","png","gif","svg","mp4","mp3","zip","exe"],
                deny=[r"/login", r"/signup", r"/cart", r"/checkout", r"\?utm_", r"#"],
                unique=True,
            ),
            callback="parse_page",
            follow=True,
        ),
    )

    def __init__(self, seeds="", max_pages=5000, *args, **kwargs):
        super().__init__(*args, **kwargs)
        seed_list = [s.strip() for s in seeds.split(",") if s.strip()]
        if not seed_list:
            # Default seed list — expand this as Neptune Browser gains users
            seed_list = [
                "https://en.wikipedia.org/wiki/Main_Page",
                "https://developer.mozilla.org/en-US/",
                "https://news.ycombinator.com/",
                "https://www.bbc.com/news",
            ]
        self.start_urls = seed_list
        self.allowed_domains = [urlparse(u).netloc for u in seed_list]
        self.max_pages = int(max_pages)
        self.pages_crawled = 0

    def parse_page(self, response):
        self.pages_crawled += 1
        if self.pages_crawled > self.max_pages:
            return

        # Extract meaningful content only
        title = response.css("title::text").get("") or response.url
        title = title.strip()[:200]

        # Get meta description
        description = (
            response.css('meta[name="description"]::attr(content)').get("")
            or response.css('meta[property="og:description"]::attr(content)').get("")
        )

        # Extract body text — skip nav, footer, ads
        body_parts = response.css(
            "main, article, .content, .post-body, p, h1, h2, h3"
        ).css("::text").getall()

        if not body_parts:
            body_parts = response.css("body ::text").getall()

        body = " ".join(t.strip() for t in body_parts if t.strip())
        body = re.sub(r"\s+", " ", body).strip()[:50000]  # cap at 50k chars

        if len(body) < 100:
            return   # Skip near-empty pages

        yield {
            "url": response.url,
            "title": title,
            "body": body,
            "description": description[:300] if description else body[:200],
            "domain": urlparse(response.url).netloc,
        }