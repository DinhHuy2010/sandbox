# pyright: standard, reportPrivateImportUsage=false, reportPrivateUsage=false

from http import cookiejar
import json

import httpx
import innertube
from innertube import api
from innertube.enums import Endpoint


def log_request(request: httpx.Request):
    print(f"Request: {request.method} {request.url}")
    for name, value in request.headers.items():
        print(f"{name}: {value}")
    if request.content:
        print(f"Body: {request.content.decode('utf-8')}")


def log_response(response: httpx.Response):
    print(f"Response: {response.status_code} {response.url}")
    print(f"Headers: {response.headers}")
    # if response.content:
    #     print(f"Body: {response.content.decode('utf-8')}")


cookiejar_data = cookiejar.MozillaCookieJar()
cookiejar_data.load("ytcookies-netscape.txt", ignore_discard=True, ignore_expires=True)
cookies_httpx = httpx.Cookies(cookiejar_data)

client = httpx.Client(
    base_url=innertube.config.base_url,
    event_hooks={
        "request": [log_request],
        "response": [log_response],
    },
    cookies=cookies_httpx,
)


class PatchCookier(innertube.InnerTubeAdaptor):
    def _build_request(
        self, endpoint: str, params: dict | None = None, body: dict | None = None
    ) -> httpx.Request:
        req = self.session.build_request(
            "POST",
            endpoint,
            params=self.context.params().update(params or {}),
            json=api.contextualise(self.context, body or {}),
            headers=self.context.headers(),
        )
        cookies_httpx.set_cookie_header(req)
        return req


itube = innertube.InnerTube("WEB")
itube.adaptor = PatchCookier(
    innertube.get_context("WEB"),  # type: ignore
    session=client,
)
print(itube.adaptor)
out = itube(
    "subscription/subscribe",
    body={"channelIds": ["UC9W1OJO0rWslExH6DLn45iw"], "params": "EgIIAhgA"},
)
with open("out.json", "w") as f:
    f.write(json.dumps(out, indent=2))


# VIDEO_ID = "lJnQChnv1T4"
# o = itube.browse("FEsubscriptions")
# o = json.dumps(o, indent=2)
# with open("o2.json", "w") as f:
#     f.write(o)
