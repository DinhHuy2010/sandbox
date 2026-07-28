import httpx
import starlette.applications
import starlette.requests
import starlette.responses
import starlette.routing
from starlette.templating import Jinja2Templates


client = httpx.Client(
    headers={"User-Agent": "wd.py (https://www.wikidata.org/wiki/User:DinhHuy2010)"},
)
templates = Jinja2Templates(directory="templates")

def wdsearch(request: starlette.requests.Request) -> starlette.responses.JSONResponse:
    query = request.query_params.get("q", "")
    if not query:
        return starlette.responses.JSONResponse([])

    url = "https://www.wikidata.org/w/api.php"
    params = {
        "action": "wbsearchentities",
        "format": "json",
        "language": "en",
        "search": query,
        "limit": 10,
    }

    response = client.get(url, params=params)
    data = response.json().get("search", [])
    results = [
        {
            "id": item["id"],
            "label": item.get("label", ""),
            "description": item.get("description", ""),
        }
        for item in data
    ]

    return starlette.responses.JSONResponse(results)


def index(request: starlette.requests.Request) -> starlette.responses.HTMLResponse:
    return templates.TemplateResponse("wikidata_search.html", {"request": request})


routes = [
    starlette.routing.Route("/", index),
    starlette.routing.Route("/wdsearch", wdsearch),
]
app = starlette.applications.Starlette(routes=routes)

