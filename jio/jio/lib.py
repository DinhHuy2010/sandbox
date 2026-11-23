from datetime import date

import niquests

JIO_CHANNELS_LIST_URL = "https://jiotvapi.cdn.jio.com/apis/v3.0/getMobileChannelList/get/?langId=6&devicetype=phone&os=android&usertype=JIO&version=343"
JIO_SCHEDULE_URL = (
    "https://jiotvapi.cdn.jio.com/apis/v1.3/getepg/get?channel_id={id}&offset={offset}"
)
SESSION = niquests.AsyncSession()


async def pull_channels_list(session: niquests.AsyncSession = SESSION):
    """
    Pulls the list of channels from the Jio API.

    Returns:
        dict: A dictionary containing the channel list.
    """
    response = await session.get(JIO_CHANNELS_LIST_URL)
    response.raise_for_status()  # Raise an error for bad responses
    return response.json()["result"]


async def pull_epg(channel_id: int, date: date, session: niquests.AsyncSession = SESSION):
    offset = (date - date.today()).days
    if offset > 0:
        raise ValueError("Date cannot be in the future.")
    response = await session.get(JIO_SCHEDULE_URL.format(id=channel_id, offset=offset))
    response.raise_for_status()  # Raise an error for bad responses
    return response.json()
