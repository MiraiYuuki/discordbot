import aiohttp
import config
import async_timeout
from datetime import datetime

from collections import namedtuple

EVENT_DATA_URL = "https://deresute.mon.moe/d?type=0&rank=1&rank=2001&rank=10001&rank=20001&rank=60001&rank=120001&event={0}"

async def cfetch(url):
    with async_timeout.timeout(5):
        async with aiohttp.get(url) as response:
            return await response.json()

cutoff_t = namedtuple("cutoff_t",
    ("name", "collected", "tiers"))
tier_t = namedtuple("tier_t",
    ("position", "points", "delta"))

class EventReader(object):
    def __init__(self):
        # self.client = peony.PeonyClient(
        #     consumer_key=config.get("deresute.app_key"),
        #     consumer_secret=config.get("deresute.app_secret"),
        #     access_token=config.get("deresute.token"),
        #     access_token_secret=config.get("deresute.token_secret"))
        pass

    async def get_cutoffs(self, event_id=None):
        # req = client.api.statuses.home_timeline.get(count=200, since_id=0)

        if event_id is None:
            h_info = await cfetch("https://starlight.kirara.ca/api/v1/happening/now")
            if not h_info["events"]:
                return

            current_event = h_info["events"][0]

            if not (999 < current_event["id"] < 2000 or 2999 < current_event["id"] < 4000):
                return
            event_id = current_event["id"]

        border_data = await cfetch(EVENT_DATA_URL.format(event_id))
        headers = border_data[0][0]
        cutoff = border_data[0][-1]

        if len(border_data[0]) > 2:
            deltas = border_data[0][-2]
        else:
            deltas = [0] * len(cutoff)

        collected = cutoff[0]
        tiers = tuple(tier_t(x, y, y - z) for x, y, z in zip(headers, cutoff[1:], deltas[1:]))

        a_cutoff = cutoff_t("Event Name", datetime.fromtimestamp(int(collected)), tiers)
        return a_cutoff
