import aiohttp
import async_timeout
import asyncio
import time
import json

async def cfetch(url):
    t = time.time()

    with async_timeout.timeout(20):
        async with aiohttp.get(url) as response:
            rsp = await response.json()
            print("cfetch({0}): completed in {1} s".format(url, time.time() - t))
            return rsp

async def ctlstrings(strings):
    if not strings:
        return {}

    t = time.time()

    try:
        with async_timeout.timeout(10):
            async with aiohttp.post("https://starlight.kirara.ca/api/v1/read_tl",
                                    data=json.dumps(strings)) as response:
                rsp = await response.json()
                print("ctlstrings({0}): completed in {1} s".format(len(strings), time.time() - t))
                return rsp
    except asyncio.TimeoutError:
        print("ctlstrings({0}): timed out".format(len(strings)))
        return {}
