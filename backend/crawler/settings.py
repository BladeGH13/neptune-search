BOT_NAME = "NeptuneCrawler"
SPIDER_MODULES = ["backend.crawler"]
NEWSPIDER_MODULE = "backend.crawler"

# Be polite — respect robots.txt
ROBOTSTXT_OBEY = True
DOWNLOAD_DELAY = 1.5           # seconds between requests
CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 2
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0

# Don't crawl media files
ALLOWED_MEDIA_TYPES = ["text/html", "application/xhtml+xml"]

USER_AGENT = (
    "NeptuneSearchBot/1.0 (Neptune Browser by BLUOM Tech; "
    "+https://github.com/BLUOM/neptune-search)"
)

# Save crawl state between runs (resumes after GitHub Action restarts)
JOBDIR = "./data/crawl-state"

# Pipeline sends pages to the search API
ITEM_PIPELINES = {
    "backend.crawler.pipeline.NeptuneIndexPipeline": 300,
}

# Limits for GitHub Actions free tier (keeps run under 6hr limit)
CLOSESPIDER_PAGECOUNT = int(__import__("os").environ.get("MAX_PAGES", "5000"))

LOG_LEVEL = "INFO"