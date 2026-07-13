"""Scrapy settings for InfiniDex Pokepedia scraper — Gen 7 USUM movesets."""

BOT_NAME = "pokepedia_scraper"

SPIDER_MODULES = ["pokepedia_scraper.spiders"]
NEWSPIDER_MODULE = "pokepedia_scraper.spiders"

# Transparent user-agent (educational project)
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0 Safari/537.36 "
    "(Educational project – Pokémon Infinite Fusion data)"
)

# Respect robots.txt
ROBOTSTXT_OBEY = True

# Rate limiting — be polite to Pokepedia (≤ ~2 req/s, robots.txt honoured,
# transparent UA, 24h HTTP cache: cold crawl ~8 min instead of ~17)
CONCURRENT_REQUESTS = 4
CONCURRENT_REQUESTS_PER_DOMAIN = 2
DOWNLOAD_DELAY = 0.75
RANDOMIZE_DOWNLOAD_DELAY = True
DOWNLOAD_TIMEOUT = 20

# Retry policy
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 522, 524, 408, 429]

# AutoThrottle
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 0.75
AUTOTHROTTLE_MAX_DELAY = 8.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0
AUTOTHROTTLE_DEBUG = False

# HTTP cache (avoid re-scraping during dev)
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 86400   # 24h
HTTPCACHE_DIR = "httpcache"
HTTPCACHE_IGNORE_HTTP_CODES = [500, 502, 503, 504]
HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

# Pipeline
ITEM_PIPELINES = {
    "pokepedia_scraper.pipelines.MovesetPipeline": 300,
}

LOG_LEVEL = "INFO"
FEED_EXPORT_ENCODING = "utf-8"
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
