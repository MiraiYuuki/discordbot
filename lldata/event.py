import aiohttp
from collections import namedtuple

event_t = namedtuple("event_t",
    ("id", "name"))
cutoff_t = namedtuple("cutoff_t",
    ("date", "hour", "t1", "t1_delta", "t1_d2",
                     "t2", "t2_delta", "t2_d2",
                     "t3", "t3_delta", "t3_d2"))

def safe_int(k):
    try:
        return int(k)
    except ValueError:
        return k

async def llsif_fetch_eventinfo():
    async with aiohttp.get("http://llsif.net/data/event_info.json") as r:
        ei_struct = await r.json()

    en_e = None
    jp_e = None

    if ei_struct["current_jp_event"]:
        jp_e = event_t(ei_struct["current_jp_event"], ei_struct["jp_events"][str(ei_struct["current_jp_event"])]["event_name"])

    if ei_struct["current_en_event"]:
        en_e = event_t(ei_struct["current_en_event"], ei_struct["en_events"][str(ei_struct["current_en_event"])]["event_name"])

    return {"JP": jp_e,
            "EN": en_e}

async def llsif_fetch_real_cutoffs(sid, event_id):
    async with aiohttp.get("http://llsif.net/data/{0}/{1}.csv".format(sid, event_id)) as r:
        the_csv = await r.text()

    fl_index = the_csv.rfind("\n", 0, len(the_csv) - 5)
    fl2_index = the_csv.rfind("\n", 0, fl_index - 1)

    ks = []
    for csvent in the_csv[fl2_index + 1:].split("\n"):
        if csvent.startswith("#") or not csvent:
            continue

        date, hour_no, t1, t1_diff, t2, t2_diff, t3, t3_diff, *dontcare = map(safe_int, csvent.split(","))
        ks.append(cutoff_t(date, hour_no, t1, t1_diff, 0, t2, t2_diff, 0, t3, t3_diff, 0))

    if len(ks) == 1:
        cur = ks[0]
        prev = cutoff_t(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    else:
        prev, cur = ks

    r =    cur._replace(t1_d2=cur.t1_delta - prev.t1_delta,
                        t2_d2=cur.t2_delta - prev.t2_delta,
                        t3_d2=cur.t3_delta - prev.t3_delta)
    return r

if __name__ == '__main__':
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(llsif_fetch_real_cutoffs("EN", 64))