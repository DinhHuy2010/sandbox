from json import loads
import httpx
import sseclient


def connect_wmrc_feed():
    """
    Connect to the WMRC SSE feed and return the HTTP response object.
    """
    url = "https://stream.wikimedia.org/v2/stream/recentchange"
    headers = {
        "Accept": "text/event-stream",
        "Cache-Control": "no-cache",
        "User-Agent": "wmrc-sse-client/1.0 (https://example.com/)",
    }

    response = httpx.stream("GET", url, headers=headers, timeout=None)
    return response


def stream_wmrc_events(response: httpx.Response):
    """
    Stream events from the WMRC SSE feed.
    """
    client = sseclient.SSEClient((b for b in response.iter_bytes()))

    for event in client.events():
        yield event


if __name__ == "__main__":
    with connect_wmrc_feed() as response:
        for event in stream_wmrc_events(response):
            p = loads(event.data)
            if p["type"] == "new":
                print(p["wiki"], p["title"], p["revision"]["new"])