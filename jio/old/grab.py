from datetime import date, timedelta

import niquests
from niquests import HTTPError

JIO_CHANNELS_LIST_URL = "https://jiotvapi.cdn.jio.com/apis/v3.0/getMobileChannelList/get/?langId=6&devicetype=phone&os=android&usertype=JIO&version=343"
JIO_SCHEDULE_URL = (
    "https://jiotvapi.cdn.jio.com/apis/v1.3/getepg/get?channel_id={id}&offset={offset}"
)
SESSION = niquests.Session()


def pull_channels_list():
    """
    Pulls the list of channels from the Jio API.

    Returns:
        dict: A dictionary containing the channel list.
    """
    response = SESSION.get(JIO_CHANNELS_LIST_URL)
    response.raise_for_status()  # Raise an error for bad responses
    return response.json()["result"]


def pull_epg(channel_id: int, date: date):
    offset = (date - date.today()).days
    if offset > 0:
        raise ValueError("Date cannot be in the future.")
    response = SESSION.get(JIO_SCHEDULE_URL.format(id=channel_id, offset=offset))
    response.raise_for_status()  # Raise an error for bad responses
    return response.json()


def check(channel_id: int, date: date):
    try:
        pull_epg(channel_id, date)
    except HTTPError as e:
        if e.response.status_code == 404:
            return False
        raise
    else:
        return True


def brute_force(channel_id: int, earliest_allowed=date(2000, 1, 1)):
    candidate = date.today()
    last_good_date = None
    step = 1

    while candidate >= earliest_allowed:
        print(f"Checking {channel_id} on {candidate}")

        if check(channel_id, candidate):
            last_good_date = candidate
            candidate = max(earliest_allowed, candidate - timedelta(days=step))
            step *= 2

            if candidate == last_good_date:
                return candidate
        else:
            if last_good_date is None:
                raise ValueError("No valid date found.")
            break
    else:
        if last_good_date is None:
            raise ValueError("No valid date found.")
        if candidate == earliest_allowed:
            return candidate
        candidate = earliest_allowed - timedelta(days=1)

    upper = last_good_date
    lower = candidate

    while (upper - lower).days > 1:
        middle = lower + (upper - lower) // 2

        print(f"Binary search checking {channel_id} on {middle}")

        if check(channel_id, middle):
            upper = middle
        else:
            lower = middle

    return upper


if __name__ == "__main__":
    ls = pull_channels_list()
    channel_list = {channel["channel_id"]: channel["channel_name"] for channel in ls}
    print(f"Got channel list: {len(channel_list)} channels found.")
    for channel_id, channel_name in channel_list.items():
        print(f"Brute forcing for {channel_name} (ID: {channel_id})")
        last_valid_date = brute_force(channel_id)
        print(
            f"Last valid date for {channel_name} (ID: {channel_id}): {last_valid_date}"
        )
