# pyright: standard

import concurrent.futures
from typing import Any, Callable, Generator, Sequence

import attrs
import httpx
from lxml import etree


def discover_wordpress_api(client: httpx.Client, url: str) -> str:
    response = client.head(url)
    api_url = None
    try:
        api_url = response.links["https://api.w.org/"]["url"]
    except KeyError:
        pass
    else:
        return api_url
    full_html_resp = client.get(url)
    tree = etree.HTML(full_html_resp.text)
    link_elem = tree.find(".//link[@rel='https://api.w.org/']")
    if link_elem is None:
        raise ValueError(f"Could not find WordPress API URL at: {url!r}")
    api_url = link_elem.get("href")
    if api_url is None:
        raise ValueError(f"Could not find WordPress API URL at: {url!r}")
    return api_url


@attrs.define(repr=False)
class Client:
    httpx_client: httpx.Client
    api_url: str
    event_hook: Callable[[str, dict[str, Any]], Any] = attrs.field(
        default=lambda event, data: None
    )

    def __enter__(self) -> "Client":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.httpx_client.close()

    def __repr__(self) -> str:
        return f"<context: api_url={self.api_url!r}>"

    @classmethod
    def from_url(
        cls,
        url: str,
        httpx_client: httpx.Client | None = None,
        event_hook: Callable[[str, dict[str, Any]], Any] = lambda event, data: None,
    ) -> "Client":
        if httpx_client is None:
            httpx_client = httpx.Client()
        api_url = discover_wordpress_api(httpx_client, url)
        event_hook("api_discovered", {"url": api_url})
        return cls(httpx_client=httpx_client, api_url=api_url, event_hook=event_hook)

    def call(
        self,
        namespace: str,
        path: str,
        params: dict[str, Any] | None = None,
        fields: Sequence[str] | None = None,
        embed: str | None = None,
    ) -> tuple[Any, int, int, int | None]:
        url = httpx.URL(self.api_url)
        url = url.join(f"{namespace}/{path}")
        query_params = params or {}
        afields = []
        if embed is not None:
            query_params["_embed"] = embed
            if fields is not None and "_embedded" not in fields:
                afields.append("_embedded")
            if fields is not None and "_links" not in fields:
                afields.append("_links")
            if fields:
                afields.extend(fields)
        if afields:
            query_params["_fields"] = ",".join(afields)
        self.event_hook("api_call", {"url": str(url), "params": query_params})
        response = self.httpx_client.get(url, params=query_params)
        data = response.json()
        if not response.is_success:
            raise httpx.HTTPStatusError(
                f"API call to {url!r} failed with status code {response.status_code} (json: {data!r})",
                request=response.request,
                response=response,
            )
        total_records = response.headers.get("X-WP-Total")
        total_pages = response.headers.get("X-WP-TotalPages")
        self.event_hook(
            "api_response",
            {
                "url": str(url),
                "data": data,
                "total_records": total_records,
                "total_pages": total_pages,
            },
        )
        return data, total_records, total_pages, query_params.get("page")

    def call_paginated(
        self,
        namespace: str,
        path: str,
        params: dict[str, Any] | None = None,
        fields: Sequence[str] | None = None,
        embed: str | None = None,
    ) -> Generator[tuple[int, Any], None, None]:
        response, _, total_pages, page = self.call(
            namespace,
            path,
            params={**(params or {}), "per_page": 100, "page": 1},
            fields=fields,
            embed=embed,
        )
        yield 1, response
        if total_pages is None:
            return
        for page in range(2, int(total_pages) + 1):
            response, _, _, page = self.call(
                namespace,
                path,
                params={**(params or {}), "per_page": 100, "page": page},
                fields=fields,
                embed=embed,
            )
            assert page
            yield page, response

    def call_paginated_concurrent(
        self,
        namespace: str,
        path: str,
        params: dict[str, Any] | None = None,
        fields: Sequence[str] | None = None,
        embed: str | None = None,
        max_concurrency: int = 5,
    ) -> Generator[tuple[int, Any], None, None]:
        response, _, total_pages, _ = self.call(
            namespace,
            path,
            params={**(params or {}), "per_page": 100, "page": 1},
            fields=fields,
            embed=embed,
        )
        yield 1, response
        if total_pages is None:
            return
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=max_concurrency
        ) as executor:
            future_to_page = []
            for page in range(2, int(total_pages) + 1):
                future = executor.submit(
                    self.call,
                    namespace,
                    path,
                    params={**(params or {}), "per_page": 100, "page": page},
                    fields=fields,
                    embed=embed,
                )
                future_to_page.append(future)
            for future in concurrent.futures.as_completed(future_to_page):
                try:
                    response, _, _, page = future.result()
                    yield page, response
                except Exception as exc:
                    print(f"API call generated an exception: {exc!r}")


def fetch_index(context: Client) -> dict[str, Any]:
    if context.api_url is None:
        raise ValueError("API URL not set in context")
    response = context.httpx_client.get(context.api_url)
    response.raise_for_status()
    index = response.json()
    context.event_hook("api_index_fetched", {"info": index})
    return index


def call_api_paginated(
    context: Client,
    namespace: str,
    endpoint: str,
    path_param: str | None = None,
    params: dict[str, Any] | None = None,
    fields: Sequence[str] | None = None,
    embed: str | None = None,
) -> Generator[Any, None, None]:
    if context.api_url is None:
        raise ValueError("API URL not set in context")
    url = httpx.URL(context.api_url)
    url = url.join(f"{namespace}/{endpoint}/")
    if path_param is not None:
        url = url.join(path_param + "/")
    query_params = params or {}
    afields = []
    if embed is not None:
        query_params["_embed"] = embed
        if fields is not None and "_embedded" not in fields:
            afields.append("_embedded")
        if fields is not None and "_links" not in fields:
            afields.append("_links")
        if fields:
            afields.extend(fields)
    if afields:
        query_params["_fields"] = ",".join(afields)
    page = 1
    while True:
        query_params["page"] = page
        context.event_hook("api_call", {"url": str(url), "params": query_params})
        response = context.httpx_client.get(url, params=query_params)
        data = response.json()
        if not response.is_success:
            raise httpx.HTTPStatusError(
                f"API call to {url!r} failed with status code {response.status_code} (json: {data!r})",
                request=response.request,
                response=response,
            )
        context.event_hook("api_response", {"url": str(url), "data": data})
        for item in data:
            yield item
        total_pages = int(response.headers.get("X-WP-TotalPages", "1"))
        if page >= total_pages:
            break
        page += 1


def event_logger(event: str, data: dict[str, Any]) -> None:
    if event == "api_discovered":
        print(f"Discovered API URL: {data['url']}")
    elif event == "api_call":
        print(f"Calling API: {data['url']} with params: {data['params']}")
    elif event == "api_response":
        print(f"Received response from API: {data['url']}")


if __name__ == "__main__":
    ctx = Client.from_url(
        "https://wordpress.org/news/",
        httpx_client=httpx.Client(follow_redirects=True),
        event_hook=event_logger,
    )
    with ctx:
        posts = ctx.call_paginated_concurrent(
            "wp/v2", "posts", params={"per_page": 100}, fields=["id", "title"]
        )
        for page, post_batch in posts:
            print(f"Page {page}: {len(post_batch)} posts")
