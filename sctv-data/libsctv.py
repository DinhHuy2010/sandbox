import zoneinfo
from datetime import UTC, date, datetime

import httpx

session = httpx.Client(
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36"
    }
)
CHANNELS_URL = "https://www.sctv.com.vn/WebMain/Kenh/LayDSKenhCoLPS"
EPG_URL = "https://www.sctv.com.vn/WebMain/LichPhatSong/LayLichPhatSong"
LOCAL_TZ = zoneinfo.ZoneInfo("Asia/Ho_Chi_Minh")


def fetch_channels():
    resp = session.post(
        CHANNELS_URL,
        json={},
        headers={
            "Content-Type": "application/json; charset=UTF-8",
        },
    )
    return resp.json()


def fetch_epg(channel_id: int, bdate: str | date):
    if isinstance(bdate, str):
        bdate = date.fromisoformat(bdate)
    dt = datetime.combine(bdate, datetime.min.time(), tzinfo=LOCAL_TZ)
    to_send = dt.astimezone(UTC).isoformat()
    resp = session.post(
        EPG_URL,
        json={"maKenh": str(channel_id), "ngay": to_send},
    )
    return resp.json()


if __name__ == "__main__":
    SCTV2 = 2
    print(fetch_epg(SCTV2, "2021-06-01"))
