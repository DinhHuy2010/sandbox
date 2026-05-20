from urllib.parse import parse_qs, urlparse

import scrapy
import scrapy.http


class PpdvnSpider(scrapy.Spider):
    name = "ppdvn"
    allowed_domains = ["ppdvn.gov.vn"]
    # start_urls = ["https://ppdvn.gov.vn"]
    start_urls = ["https://ppdvn.gov.vn/web/guest/tra-cuu-luu-chieu"]

    def _parse_table_data(self, response: scrapy.http.Response):
        table = response.css("div#list_data_return > table")
        header = table.css("thead > tr > th::text").getall()
        data = table.css("tbody > tr")
        for row in data:
            yield {
                header[i].strip(): (cell.css("::text").get() or "").strip()
                for i, cell in enumerate(row.css("td"))
            }

    def parse(self, response: scrapy.http.Response):
        yield from self._parse_table_data(response)

        # Parse pagination
        parsed = urlparse(response.url)
        query_params = parse_qs(parsed.query)
        current_page = query_params.get("p", [1])[0]

        if int(current_page) > 1:
            return

        last_page = response.css("div.pagination > ul > li > a::attr(href)")[-1].get()
        last_page_number = parse_qs(urlparse(last_page).query).get("p", [None])[0]
        # print("Last page number:", last_page_number)
        if last_page_number is not None:
            urls = (
                f"https://ppdvn.gov.vn/web/guest/tra-cuu-luu-chieu?&p={page}"
                for page in range(2, int(last_page_number) + 1)
            )
            yield from response.follow_all(urls, callback=self.parse)
