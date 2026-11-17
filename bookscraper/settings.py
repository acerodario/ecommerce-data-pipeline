import os

BOT_NAME = "bookscraper"
SPIDER_MODULES = ["bookscraper.spiders"]
NEWSPIDER_MODULE = "bookscraper.spiders"

USER_AGENT = "ecommerce-data-pipeline (+https://github.com/acerodario/ecommerce-data-pipeline)"
ROBOTSTXT_OBEY = True

# Rastreo respetuoso: concurrencia moderada y autothrottle
CONCURRENT_REQUESTS_PER_DOMAIN = 8
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 0.5
AUTOTHROTTLE_TARGET_CONCURRENCY = 4.0
RETRY_TIMES = 3

ITEM_PIPELINES = {
    "bookscraper.pipelines.ValidatePipeline": 100,
    "bookscraper.pipelines.DedupPipeline": 200,
    "bookscraper.pipelines.PostgresPipeline": 300,
}

DATABASE_URL = os.getenv("DATABASE_URL")
DB_BATCH_SIZE = 100

FEED_EXPORT_ENCODING = "utf-8"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
