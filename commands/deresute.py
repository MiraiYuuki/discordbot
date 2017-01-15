import deresdata
import aiohttp
import asyncio
import async_timeout
import json
import discord
import sqlite3
import time
import sys

import loader
import auth

P_DERESUTE_PUBLIC = auth.declare_right("DERESUTE_PUBLIC")
P_DERESUTE_NOISY  = auth.declare_right("DERESUTE_NOISY")
P_DERESUTE_ADMIN  = auth.declare_right("DERESUTE_ADMIN")

class IDAlreadyExistsError(Exception):
    pass
class NameNeedsOneOrMoreNonNumbersError(Exception):
    pass
class IDNotDeletedError(Exception):
    pass
class IDInvalidError(Exception):
    pass

@loader.context_class
class FriendDB(object):
    def __init__(self):
        connection = sqlite3.connect("drst_game_ids.db")
        connection.execute("""CREATE TABLE IF NOT EXISTS
            gameids_v1 (
                _gameid TEXT,
                _originator TEXT,
                _name TEXT,
                _lower TEXT
            )
        """)
        connection.commit()

        self.connection = connection

    def set_id_for_name(self, name, id, originator):
        if self.get_id_for_name(name):
            raise IDAlreadyExistsError()

        if name.isdigit():
            raise NameNeedsOneOrMoreNonNumbersError()

        if not id.isdigit():
            raise IDInvalidError()

        self.connection.execute("INSERT INTO gameids_v1 VALUES (?, ?, ?, ?)", (id, originator, name, name.lower()))
        self.connection.commit()

    def delete_name(self, name):
        self.connection.execute("DELETE FROM gameids_v1 WHERE _lower = ?", (name.lower(),))
        self.connection.commit()

    def delete_name_safe(self, name, originator):
        k = self.connection.execute("DELETE FROM gameids_v1 WHERE _lower = ? AND _originator = ?", (name.lower(), originator))

        if k.rowcount == 0:
            raise IDNotDeletedError()
        else:
            self.connection.commit()

    def get_id_for_name(self, name):
        k = self.connection.execute("SELECT _gameid FROM gameids_v1 WHERE _lower = ?", (name.lower(),)).fetchone()

        if k is None:
            return None
        else:
            return k[0]

DERESUTE = loader.register_command("deresute", "drst", "dere", "ss",
    description="umbrella command for the deresute module - private API free for 0 days")

@DERESUTE.subcommand("card",
    description="Show details for a certain card.",
    synopsis="[search terms...]",
    examples=["syuko2", "event mayu", "ssr riina"])
@auth.requires_right(P_DERESUTE_PUBLIC)
async def card(context, message, content):
    await context.client.send_typing(message.channel)

    api_info = await cfetch("https://starlight.kirara.ca/api/v1/info")
    if deresdata.needs_update(str(api_info["truth_version"])):
        print("Building ark...")
        await deresdata.build_ark()

    try:
        t1 = time.time()
        query = deresdata.parse_query(content)
        results = deresdata.exec_query(query)
        print("exec time:", time.time() - t1)
    except deresdata.InvalidQueryError as error:
        return await context.client.send_message(message.channel, "{0} {1}".format(
            message.author.mention,
            str(error)
        ))

    if not results:
        return await context.client.send_message(message.channel,
            "There aren't any cards matching your search, nya.")
    else:
        fc = results[0]

    ep = "https://starlight.kirara.ca/api/v1/card_t/{0},{1}".format(fc.root_id, fc.awakened_id)
    try:
        card_json = await cfetch(ep)
    except asyncio.TimeoutError:
        return await client.send_message(message.channel, "timed out :(")

    c1, c2 = card_json["result"]

    try:
        tl_dictionary = await ctlstrings(tl_request_from_card_json(c1))
    except Exception as e:
        tl_dictionary = {}
        print(e)

    await context.client.send_message(message.channel, embed=embed_from_card_json(c1, c2, tl_dictionary))

    if len(results) > 1:
        if len(results) - 1 != 1:
            fmt = "{0} more results, nya. Their IDs are {1}. Display them using `deresute card '[id]`."
        else:
            fmt = "{0} more result, nya. Display it using `deresute card '{1}`."

        await context.reply(fmt.format(
            len(results) - 1, ", ".join(map(lambda x: str(x.root_id), results[1:])) ))

@DERESUTE.subcommand("whatsnew",
    description="Display the latest update.")
@auth.requires_right(P_DERESUTE_NOISY)
async def whatsnew(context, message, content):
    context.client.send_typing(message.channel)

    history = await cfetch("https://starlight.kirara.ca/api/private/history")
    first = history["result"][0]

    fetch_data_list = []

    cl = json.loads(first["added_cards"])
    for lst in cl.values():
        fetch_data_list.extend(lst)

    ep = "https://starlight.kirara.ca/api/v1/card_t/" + ",".join(map(str, fetch_data_list))
    cards = await cfetch(ep)
    tl_list = list(set(sum((tl_request_from_card_json(c) for c in cards["result"]), [])))

    try:
        tl_dictionary = await ctlstrings(tl_list)
    except Exception as e:
        tl_dictionary = {}
        print(e)

    await context.reply("Last update added {0} card(s), nya.".format(len(fetch_data_list)))

    for cjson in cards["result"]:
        await context.reply(embed=embed_from_card_json(cjson, cjson, tl_dictionary))

async def cfetch(url):
    with async_timeout.timeout(5):
        async with aiohttp.get(url) as response:
            return await response.json()

async def ctlstrings(strings):
    if not strings:
        return {}

    with async_timeout.timeout(5):
        async with aiohttp.post("https://starlight.kirara.ca/api/v1/read_tl",
                                data=json.dumps(strings)) as response:
            return await response.json()

def tl_request_from_card_json(c1):
    sl = []

    if c1["title_flag"]:
        sl.append(c1["title"])
    if c1["skill"]:
        sl.append(c1["skill"]["skill_name"])
    if c1["lead_skill"]:
        sl.append(c1["lead_skill"]["name"])

    return sl

def embed_from_card_json(c1, c2, tl_dictionary):
    embed = discord.Embed(title="", type="rich")
    embed.set_thumbnail(url="https://hoshimoriuta.kirara.ca/icon_card/{0}.png".format(c1["id"]))
    embed.url = "https://starlight.kirara.ca/card/{0}".format(c1["id"])

    COLOURS = {"cute": 0xFF0063, "cool": 0x006BFF, "passion": 0xFFA907}
    BEST_STAT = {2: "Dance", 1: "Visual", 3: "Vocal"}
    archetype = "{1} {0}".format(c1["attribute"].title(), BEST_STAT.get(c2["best_stat"], "Balanced"))

    if c1["title_flag"]:
        embed.title = "[{0}] {1}".format(tl_dictionary.get(c1["title"], c1["title"]), c1["chara"]["conventional"])
    else:
        embed.title = "{0}".format(c1["chara"]["conventional"])

    embed.colour = COLOURS.get(c1["attribute"])

    embed.add_field(name="Archetype", value=archetype, inline=True)

    embed.add_field(
        name="Vo/Vi/Da (max)",
        value="{3}{0}{3} / {4}{1}{4} / {5}{2}{5}".format(
            c2["vocal_max"] + c2["bonus_vocal"],
            c2["visual_max"] + c2["bonus_visual"],
            c2["dance_max"] + c2["bonus_dance"],
            "__" if c2["best_stat"] == 3 else "",
            "__" if c2["best_stat"] == 1 else "",
            "__" if c2["best_stat"] == 2 else ""),
        inline=True)

    if c1["skill"]:
        embed.add_field(
            name="Skill: *{0}*".format(tl_dictionary.get(c1["skill"]["skill_name"], c1["skill"]["skill_name"])),
            value=c1["skill"]["explain_en"],
            inline=False)

    if c1["lead_skill"]:
        embed.add_field(
            name="Leader Skill: *{0}*".format(tl_dictionary.get(c1["lead_skill"]["name"], c1["lead_skill"]["name"])),
            value=c1["lead_skill"]["explain_en"],
            inline=False)

    return embed

# -x-  ADMIN COMMANDS  -x-

@DERESUTE.subcommand("buildkeywords")
@auth.requires_right(P_DERESUTE_ADMIN)
async def adm_buildkeywords(context, message, content):
    kwresult = await deresdata.build_keywords()
    await context.reply(str(kwresult))

@DERESUTE.subcommand("forcereloaddata", "fr")
@auth.requires_right(P_DERESUTE_ADMIN)
async def adm_forcereloaddata(context, message, content):
    global deresdata
    del deresdata

    for key in list(sys.modules.keys()):
        if key.startswith("deresdata.") or key == "deresdata":
            print(key)
            del sys.modules[key]

    import deresdata
    await context.reply("ok")

# -x- ID

@DERESUTE.subcommand("id",
    description="Fetches profiles from deresute.me.")
@auth.requires_right(P_DERESUTE_PUBLIC)
async def get_id(context, message, content):
    if content.isdigit():
        return await context.reply("https://deresute.me/{0}/medium.png?{1}".format(
            content, time.time()))

    the_id = context.get_id_for_name(content)
    if the_id is not None:
        return await context.reply("https://deresute.me/{0}/medium.png?{1}".format(
            the_id, time.time()))
    else:
        return await context.reply("Not found.")

@get_id.subcommand("add",
    description="Add your name to the database.",
    synopsis="[name] [id]")
@auth.requires_right(P_DERESUTE_PUBLIC)
async def add_id(context, message, content):
    args = content.rsplit(maxsplit=1)
    if len(args) != 2:
        return await context.reply("Provide a name and ID.")

    try:
        context.set_id_for_name(args[0], args[1], message.author.id)
    except IDAlreadyExistsError:
        await context.reply("Name is already in use. `del` it and try again.")
    except NameNeedsOneOrMoreNonNumbersError:
        await context.reply("Please include at least one non-number in your name.")
    except IDInvalidError:
        await context.reply("The ID is not valid.")
    else:
        try:
            await context.client.add_reaction(message, "\u2705")
        except discord.errors.Forbidden:
            await context.reply("\u2705")

@get_id.subcommand("delete", "del",
    description="Remove your name from the database.",
    synopsis="[name]")
@auth.requires_right(P_DERESUTE_PUBLIC)
async def del_id_safe(context, message, content):
    try:
        context.delete_name_safe(content, message.author.id)
    except IDNotDeletedError:
        await context.reply("Name wasn't deleted. Are you sure it belongs to you?")
    else:
        try:
            await context.client.add_reaction(message, "\u2705")
        except discord.errors.Forbidden:
            await context.reply("\u2705")

@get_id.subcommand("delete!", "del!",
    description="Remove a name from the database.",
    synopsis="[name]")
@auth.requires_right(P_DERESUTE_ADMIN)
async def del_id_notsafe(context, message, content):
    context.delete_name(content)

    try:
        await context.client.add_reaction(message, "\u2705")
    except discord.errors.Forbidden:
        await context.reply("\u2705")

# -x- Events

@DERESUTE.subcommand("event", "tiers", "cutoffs", "e")
@auth.requires_right(P_DERESUTE_ADMIN)
async def get_event(context, message, content):
    cutoff = await deresdata.EventReader().get_cutoffs(int(content))

    await context.reply(embed=embed_from_cutoff(cutoff))

def embed_from_cutoff(cutoff):
    embed = discord.Embed(type="rich")

    embed.title = "bungus"
    embed.add_field(name=cutoff.name, value="{0}".format(
        cutoff.collected), inline=False)

    cutoff_content = "\n".join([
        "{0.position}:\t {0.points} pts (+{0.delta})".format(tier)
        for tier in cutoff.tiers])
    embed.add_field(name="Cutoffs", value=cutoff_content, inline=False)

    # r = random.randint(25, 256)
    # g = random.randint(25, 256)
    # b = random.randint(25, 256)
    # embed.colour = (r << 16) | (g << 8) | b

    return embed
