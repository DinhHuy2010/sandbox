import re
from collections import defaultdict
from datetime import datetime

import httpx
from lxml.html import fromstring
from pydantic import BaseModel, RootModel

HEADERS = {"User-Agent": "lwn-scrape/1.0"}

client = httpx.Client(headers=HEADERS)


class LWNArticle(BaseModel):
    title: str
    url: str
    author: str
    publish_date: datetime | None

class LWNArticles(RootModel[list[LWNArticle]]):
    root: list[LWNArticle]


def scrape_guestindex(client: httpx.Client = client) -> LWNArticles:
    html = client.get("https://lwn.net/Archives/GuestIndex/")
    html.raise_for_status()
    tree = fromstring(html.content)
    ls = tree.cssselect("div.ArticleText")[0]
    current_author = None
    result: dict[str, list[tuple[str, str, str | None]]] = defaultdict(list)
    for entry in ls.iter("p"):
        ty = entry.get("class")
        if ty == "IndexPrimary":
            current_author = entry.text_content().strip().rstrip(":")
        elif ty == "IndexEntry":
            entry.make_links_absolute("https://lwn.net/")
            link = entry.cssselect("a")[0]
            href = link.get("href")
            if href is None:
                continue
            title = link.text_content().strip()
            raw = entry.text_content()
            # Extract publish date (such as December 12, 2023) from the raw text
            result_match = re.search(
                r"\b(January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, \d{4}\b",
                raw,
            )
            publish_date = result_match.group(0) if result_match else None
            if current_author is not None:
                result[current_author].append((title, href, publish_date))

    parsed: list[LWNArticle] = []
    for author, articles in result.items():
        for title, url, publish_date in articles:
            parsed.append(
                LWNArticle(
                    title=title,
                    url=url,
                    author=author,
                    publish_date=datetime.strptime(publish_date, "%B %d, %Y")
                    if publish_date
                    else None,
                )
            )
    return LWNArticles(root=parsed)


p = scrape_guestindex(client)
print(p.model_dump_json(indent=2))
