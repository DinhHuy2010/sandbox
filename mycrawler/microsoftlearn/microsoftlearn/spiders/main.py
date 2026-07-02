import re
from urllib.parse import urlparse

import scrapy
import scrapy.http
import scrapy.spiders

EN_US_REGEX = re.compile(r".+_en-us_.+\.xml", re.MULTILINE | re.UNICODE)


class MainSpider(scrapy.spiders.SitemapSpider):
    name = "main"
    allowed_domains = ["learn.microsoft.com"]
    # sitemap_urls = ["https://learn.microsoft.com/"]
    # start_urls = ["https://learn.microsoft.com"]
    sitemap_urls = ["https://learn.microsoft.com/_sitemaps/sitemapindex.xml"]

    def sitemap_filter(self, entries):
        for entry in entries:
            if "/_sitemaps/" in entry["loc"]:
                fn = entry["loc"].split("/")[-1]
                if EN_US_REGEX.match(fn):
                    yield entry
            else:
                url = urlparse(entry["loc"])
                url = url._replace(query="accept=text/markdown")
                entry["loc"] = url.geturl()
                yield entry

    def parse(self, response: scrapy.http.Response):
        # print(response)
        yield {
            "url": response.url,
            "content": response.text,
            "content_type": response.headers.get("Content-Type", b"").decode("utf-8"),
        }
