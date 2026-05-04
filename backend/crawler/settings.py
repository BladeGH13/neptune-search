BOT_NAME = "NeptuneCrawler"
SPIDER_MODULES = ["backend.crawler.spider"]
NEWSPIDER_MODULE = "backend.crawler"

# Be polite — respect robots.txt
ROBOTSTXT_OBEY = True
DOWNLOAD_DELAY = 1.5
CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 2
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0

USER_AGENT = (
    "NeptuneSearchBot/1.0 (Neptune Browser by BLUOM Tech; "
    "+https://github.com/BladeGH13/neptune-search)"
)

JOBDIR = "./data/crawl-state"

ITEM_PIPELINES = {
    "backend.crawler.pipeline.NeptuneIndexPipeline": 300,
}

CLOSESPIDER_PAGECOUNT = int(__import__("os").environ.get("MAX_PAGES", "5000"))

LOG_LEVEL = "INFO"