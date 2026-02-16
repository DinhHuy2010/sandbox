from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime

import httpx
from pydantic import BaseModel, RootModel
from tqdm import tqdm

START_DATE = datetime.date(2021, 6, 19)
END_DATE = datetime.date.today() + datetime.timedelta(days=20)
client = httpx.Client(limits=httpx.Limits(max_connections=None))


def on_request(request: httpx.Request) -> None:
    print("Sending request:", request.url)


def on_response(response: httpx.Response) -> None:
    print("Received response:", response.status_code, "for", str(response.url))


# client.event_hooks["request"].append(on_request)
# client.event_hooks["response"].append(on_response)


class WordleResponse(BaseModel):
    id: int
    solution: str
    print_date: datetime.date
    days_since_launch: int = 0
    editor: str | None = None


class AllWordleResponses(RootModel[dict[datetime.date, WordleResponse]]):
    root: dict[datetime.date, WordleResponse]


def drange(start: datetime.date, end: datetime.date):
    """Generate dates from start to end, inclusive."""
    current = start
    while current <= end:
        yield current
        current += datetime.timedelta(days=1)


def fetch_wordle(client: httpx.Client, date: datetime.date) -> WordleResponse:
    url = f"https://www.nytimes.com/svc/wordle/v2/{date.isoformat()}.json"
    response = client.get(url)
    response.raise_for_status()
    return WordleResponse.model_validate(response.json())


all_wordle: dict[datetime.date, WordleResponse] = {}

with ThreadPoolExecutor(max_workers=10) as executor:
    futures = [
        executor.submit(fetch_wordle, client, date)
        for date in drange(START_DATE, END_DATE)
    ]
    for future in tqdm(as_completed(futures), total=len(futures)):
        wordle = future.result()
        all_wordle[wordle.print_date] = wordle

sorted = dict(sorted(all_wordle.items(), key=lambda item: item[0]))
model = AllWordleResponses.model_validate(sorted)
with open("wordles_concurrent.json", "w") as f:
    f.write(model.model_dump_json(indent=4))
