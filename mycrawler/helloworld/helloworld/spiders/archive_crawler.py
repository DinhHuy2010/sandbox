import scrapy
from scrapy.spiders import Spider
from urllib.parse import urlencode


class ArchiveCrawlerSpider(Spider):
    name = "archive-crawler"
    query = "collection:nasa"

    base_url = "https://archive.org/services/search/v1/scrape"

    custom_settings = {
        "SPIDER_MIDDLEWARES": {
            "scrapy.spidermiddlewares.referer.RefererMiddleware": None,
        }
    }

    async def start(self):
        params = {
            "fields": "*",
            "q": self.query,
            "count": 100,
        }

        url = f"{self.base_url}?{urlencode(params)}"
        yield scrapy.Request(url, callback=self.parse)

    def parse(self, response):
        data = response.json()
        self.logger.info(f"Fetched {len(data['items'])} items, cursor: {data['cursor']}")

        for item in data["items"]:
            yield item

        cursor = data.get("cursor")
        self.logger.info(
            {k: v for k, v in data.items() if k != "items"}
        )

        if cursor:
            params = {
                "fields": "*",
                "q": self.query,
                "count": 100,
                "cursor": cursor,
            }
            self.logger.info(f"Fetching next page with cursor: {cursor}")

            next_url = f"{self.base_url}?{urlencode(params)}"

            yield response.follow(next_url, callback=self.parse)