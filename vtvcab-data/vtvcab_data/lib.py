from datetime import UTC, date, datetime
from typing import Any

import msgspec
import niquests

BASE_URL = (
    "https://apigateway.vtvcab.vn/mycab/api/v2/landing-page/broadcast_list?date={date}"
)

SESSION = niquests.AsyncSession()


class DataResponse(msgspec.Struct):
    requested_date_listing: date
    requested_at: datetime
    data: dict[str, Any]


async def pull_listing(d: date, session: niquests.AsyncSession = SESSION):
    REQUESTED_AT = datetime.now(UTC)
    url = BASE_URL.format(date=d.isoformat())
    resp = await session.get(url)
    resp.raise_for_status()
    return DataResponse(
        requested_date_listing=d,
        requested_at=REQUESTED_AT,
        data=resp.json(),
    )
