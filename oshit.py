import logging
from urllib.parse import quote as urlencode

import fastapi
from httpx import AsyncClient

app = fastapi.FastAPI()
# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
sh = logging.StreamHandler()
sh.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
logger.addHandler(sh)


async def client():
    async with AsyncClient(
        headers={"User-Agent": "oshit/0.1 (example.com)"},
        # event_hooks={"request": [on_request], "response": [on_response]},
    ) as client:
        yield client


@app.get("/", response_class=fastapi.responses.PlainTextResponse)
async def home():
    return "Hello, world!"


@app.get("/proxy/{file}")
async def proxy(file: str, client: AsyncClient = fastapi.Depends(client)):
    logger.info(f"Proxying file: {file}")
    url = "https://commons.wikimedia.org/wiki/Special:FilePath/" + urlencode(file)
    request = client.build_request("GET", url)
    response = await client.send(request, follow_redirects=True, stream=True)

    async def stream():
        try:
            async for chunk in response.aiter_raw():
                yield chunk
        finally:
            await response.aclose()

    headers = {
        "Content-Type": response.headers.get(
            "Content-Type", "application/octet-stream"
        ),
        # "Content-Length": response.headers.get("Content-Length", "0"),
        "X-Original-URL": url,
    }

    return fastapi.responses.StreamingResponse(
        stream(), headers=headers, status_code=response.status_code
    )
    # return fastapi.responses.RedirectResponse(url=url)
