from datetime import date
import json

import niquests


CHANNELS_CATALOG_URL = "https://api.vtvdigital.org/display/v21.0/catalogs/with-channels"
EPG_CATALOG_URL = "https://api.vtvdigital.org/display/v21.0/epg/"
EPG_URL = "https://api.vtvdigital.org/display/v21.0/epg"
session = niquests.Session()


def get_channels_catalog():
    response = session.get(CHANNELS_CATALOG_URL)
    response.raise_for_status()
    return response.json()


def get_channel_epg(
    channel_ids: list[str], date_from: date, date_to: date | None = None
):
    query = {}
    channels = ",".join(channel_ids)
    query["channelIDs"] = channels
    query["from"] = date_from.isoformat()
    if date_to:
        query["to"] = date_to.isoformat()
    response = session.get(EPG_URL, params=query)
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    from datetime import date

    # print(json.dumps(get_channel_epg(["1"], date.today())))
    print(json.dumps(get_channels_catalog(), indent=2))
