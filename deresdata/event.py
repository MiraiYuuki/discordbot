import config
import pytz
from . import httputils
from datetime import datetime

from collections import namedtuple

EVENT_DATA_URL = "https://deresute.mon.moe/d?type=0&rank=1&rank=2001&rank=10001&rank=20001&rank=60001&rank=120001&event={0}"
EVENT_DATA2_URL = "https://api.tachibana.cool/v1/starlight/event/{0}/ranking_list.json"
JST = pytz.timezone("Asia/Tokyo")

cutoff_t = namedtuple("cutoff_t",
    ("name", "collected", "tiers"))
tier_t = namedtuple("tier_t",
    ("position", "points", "delta"))

class NoCutoffCurrentlyAvailableError(Exception):
    pass

class NoCurrentEventError(Exception):
    pass

class CurrentEventNotRankingError(Exception):
    pass

class EventReader(object):
    def __init__(self):
        # self.client = peony.PeonyClient(
        #     consumer_key=config.get("deresute.app_key"),
        #     consumer_secret=config.get("deresute.app_secret"),
        #     access_token=config.get("deresute.token"),
        #     access_token_secret=config.get("deresute.token_secret"))

        self.cutoff_cache = None

    def is_cutoff_stale(self, cutoff):
        if self.cutoff_cache is None:
            return 1

        delta = pytz.utc.localize(datetime.now()) - cutoff.collected
        if (delta.days * 86400) + delta.seconds >= 3600:
            return 1
        else:
            return 0

    def is_valid_event_id(self, eid):
        if not (999 < eid < 2000 or 2999 < eid < 4000):
            return 0

        return 1

    async def get_current(self):
        h_info = await httputils.cfetch("https://starlight.kirara.ca/api/v1/happening/now")
        # h_info = {"events": [
        #     {"id": 3013,
        #      "name": "LIVE Groove Visual burst",
        #      "start_date": 1484719200.0,
        #      "end_date": 1484805599.0}
        # ]}

        if not h_info["events"]:
            raise NoCurrentEventError()

        current_event = h_info["events"][0]
        event_id = current_event["id"]

        return current_event

    async def get_cutoffs_from_deresute_mon_moe(self, event_id):
        # req = client.api.statuses.home_timeline.get(count=200, since_id=0)

        if not self.is_valid_event_id(event_id):
            raise CurrentEventNotRankingError()

        if not self.is_cutoff_stale(self.cutoff_cache):
            return self.cutoff_cache

        border_data = await httputils.cfetch(EVENT_DATA_URL.format(event_id))
        headers = border_data[0][0]
        cutoff = border_data[0][-1]

        if len(border_data[0]) > 2:
            deltas = border_data[0][-2]
        else:
            deltas = [0] * len(cutoff)

        collected = cutoff[0]
        tiers = tuple(tier_t(x, y, y - z) for x, y, z in zip(headers, cutoff[1:], deltas[1:]))

        a_cutoff = cutoff_t("Event Name", pytz.utc.localize(datetime.utcfromtimestamp(int(collected))), tiers)
        self.cutoff_cache = a_cutoff
        return a_cutoff

    async def get_cutoffs(self, event_id):
        if not self.is_valid_event_id(event_id):
            raise CurrentEventNotRankingError()

        if not self.is_cutoff_stale(self.cutoff_cache):
            return self.cutoff_cache

        border_data = await httputils.cfetch(EVENT_DATA2_URL.format(event_id))

        if not border_data:
            raise NoCutoffCurrentlyAvailableError()

        cutoff = border_data[-1]
        deltas = {k: 0 for k in cutoff}

        for deltas in reversed(border_data[:-1]):
            if deltas["date"].endswith(":00"):
                break

        brackets = config.get("deresute.tier_boundaries", "0,0,0,0,0")
        brackets = tuple(map(int, brackets.split(",")))

        collected = JST.localize(datetime.strptime(cutoff["date"], "%Y/%m/%d %H:%M")).astimezone(pytz.utc)

        tiers = [
            tier_t(1, cutoff["rank1"], cutoff["rank1"] - deltas["rank1"])
        ]

        for br_id, tier in enumerate(["reward" + str(n) for n in range(1, 6)]):
            tiers.append(tier_t(brackets[br_id], cutoff[tier], cutoff[tier] - deltas[tier]))

        a_cutoff = cutoff_t("Event Name", collected, tiers)
        self.cutoff_cache = a_cutoff
        return a_cutoff
