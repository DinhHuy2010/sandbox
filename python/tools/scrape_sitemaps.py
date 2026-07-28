from concurrent.futures import ThreadPoolExecutor, Future, wait
import sys
from typing import Any, Callable
from pydantic import AnyHttpUrl
from pydantic.dataclasses import dataclass
from datetime import date
import httpx
from lxml.etree import iterparse
from urllib.robotparser import RobotFileParser

from python.lib.breader import BReader

USER_AGENT = "Googlebot/2.1 (+http://www.google.com/bot.html)"
ROBOTS_TXT = "https://learn.microsoft.com/robots.txt"
robot_parser = RobotFileParser()
robot_parser.set_url(ROBOTS_TXT)
robot_parser.read()
HEADERS = {"User-Agent": USER_AGENT}
client = httpx.Client(headers=HEADERS, timeout=10.0)


@dataclass
class Sitemap:
    url: AnyHttpUrl
    last_modified: date | None


@dataclass
class Location:
    url: AnyHttpUrl
    last_modified: date | None
    change_frequency: str | None
    priority: float | None


@dataclass
class SitemapIndex:
    sitemaps: list[Sitemap]


@dataclass
class UrlSet:
    locations: list[Location]


def read_sitemap(
    client: httpx.Client,
    sitemap: str,
    on_sitemap: Callable[[Sitemap], Any] | None = None,
    on_location: Callable[[Location], Any] | None = None,
) -> None:
    with client.stream("GET", sitemap) as response:
        response.raise_for_status()
        it = response.iter_bytes()
        reader = BReader(it)
        context = iterparse(
            source=reader,
            events=("end",),
            tag=(
                "{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap",
                "{http://www.sitemaps.org/schemas/sitemap/0.9}url",
            ),
        )
        for _, elem in context:
            if elem.tag == "{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap":
                loc = elem.find("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
                if loc is None or loc.text is None:
                    continue
                lastmod = elem.find(
                    "{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod"
                )
                sitemap_obj = Sitemap(
                    url=loc.text,  # type: ignore
                    last_modified=date.fromisoformat(lastmod.text)  # type: ignore
                    if lastmod is not None
                    else None,  # type: ignore
                )
                if on_sitemap:
                    on_sitemap(sitemap_obj)
            elif elem.tag == "{http://www.sitemaps.org/schemas/sitemap/0.9}url":
                loc = elem.find("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
                if loc is None or loc.text is None:
                    continue
                lastmod = elem.find(
                    "{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod"
                )
                changefreq = elem.find(
                    "{http://www.sitemaps.org/schemas/sitemap/0.9}changefreq"
                )
                priority = elem.find(
                    "{http://www.sitemaps.org/schemas/sitemap/0.9}priority"
                )
                location_obj = Location(
                    url=loc.text,  # type: ignore
                    last_modified=date.fromisoformat(lastmod.text)  # type: ignore
                    if lastmod is not None
                    else None,
                    change_frequency=changefreq.text
                    if changefreq is not None
                    else None,
                    priority=float(priority.text) if priority is not None else None,  # type: ignore
                )
                if on_location:
                    on_location(location_obj)
            elem.clear()


def perform_scrape():
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures: list[Future[Any]] = []

        def handle_sitemap(sitemap: Sitemap) -> None:
            if robot_parser.can_fetch(USER_AGENT, str(sitemap.url)):
                futures.append(executor.submit(
                    read_sitemap,
                    client,
                    str(sitemap.url),
                    on_location=handle_location,
                ))

        def handle_location(location: Location) -> None:
            print(f"Found URL: {location.url}")

        for sitemap_url in robot_parser.site_maps() or []:
            if robot_parser.can_fetch(USER_AGENT, sitemap_url):
                futures.append(executor.submit(
                    read_sitemap,
                    client,
                    sitemap_url,
                    on_sitemap=handle_sitemap,
                ))
        try:
            wait(futures)
        except KeyboardInterrupt:
            print("Scraping interrupted by user.")
            sys.exit(1)
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    perform_scrape()
