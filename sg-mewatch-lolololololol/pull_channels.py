import json
from urllib.parse import urlencode

import niquests

MEWATCH_ALL_CHANNELS_LIST_URL = "https://cdn.mewatch.sg/api/lists/239614"

SESSION = niquests.Session()


def pull_list(page: int):
    query = {"page": page, "page_size": 50, "segments": "all"}
    response = SESSION.get(MEWATCH_ALL_CHANNELS_LIST_URL, params=query)
    response.raise_for_status()
    return response.json()


def paginate_list():
    initial_url = f"{MEWATCH_ALL_CHANNELS_LIST_URL}?{urlencode({'page': 1, 'page_size': 50, 'segments': 'all'})}"
    while True:
        response = SESSION.get(initial_url)
        response.raise_for_status()
        data = response.json()
        yield data
        if not data["paging"].get("next"):
            break
        initial_url = f"https://cdn.mewatch.sg/api{data['paging']['next']}"


for page_data in paginate_list():
    for channel in page_data.get("items", []):
        print(json.dumps(channel, ensure_ascii=False))
        
