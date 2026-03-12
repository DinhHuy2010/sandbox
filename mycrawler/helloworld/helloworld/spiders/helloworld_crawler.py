import scrapy
import scrapy.http


class HelloworldCrawlerSpider(scrapy.Spider):
    name = "helloworld-crawler"
    allowed_domains = ["pypi.org"]
    start_urls = ["https://pypi.org/simple/"]
    custom_settings = {"ROBOTSTXT_OBEY": False}

    def parse(self, response: scrapy.http.Response):
        urls = response.css("a::attr(href)")
        yield from response.follow_all(urls, self.parse_package)
        
    def parse_package(self, response: scrapy.http.Response):
        # print()
        pass
