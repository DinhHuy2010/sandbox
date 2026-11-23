from datetime import date, datetime
from typing import Any

import msgspec


class AboutResponse(msgspec.Struct):
    http_status_code: int
    http_url: str
    http_response_headers: dict[str, str]
    channel_id: int
    date_requested: date


class DataResponse(msgspec.Struct):
    raw_data: Any
    about: AboutResponse
    last_crawl: datetime
