import lldata
import discord
import random

import loader
import auth

P_SIF_PUBLIC = auth.declare_right("SIF_PUBLIC")

sif = loader.register_command("sif",
    description="Umbrella command for SIF.")

@sif.subcommand("cutoffs",
    description="Retrieve current event cutoffs.",
    synopsis="[en | jp]")
@auth.requires_right(P_SIF_PUBLIC)
async def sif_cutoffs(context, message, text):
    events = await lldata.llsif_fetch_eventinfo()

    if text == "en":
        sid = "EN"
    else:
        sid = "JP"

    evt = events[sid]
    cutoff = await lldata.llsif_fetch_real_cutoffs(sid, evt.id)

    embed = embed_from_cutoff(evt, cutoff)
    embed.url = "http://llsif.net/index.html?s={0}&e={1}".format(sid, evt.id)
    embed.set_footer(text="llsif.net")

    await context.reply(embed=embed)

# -x-

def embed_from_cutoff(event, cutoff):
    embed = discord.Embed(type="rich")

    embed.title = event.name
    embed.add_field(name="Updated", value="{0}, {1} hour(s) in.".format(
        cutoff.date, cutoff.hour), inline=False)

    cutoff_content = "\n".join([
        "T1: **{0} (+{1})** {2}".format(cutoff.t1, cutoff.t1_delta, "slowing down" if cutoff.t1_d2 >= 0 else ""),
        "T2: **{0} (+{1})** {2}".format(cutoff.t2, cutoff.t2_delta, "slowing down" if cutoff.t2_d2 >= 0 else ""),
        "T3: {0} (+{1}) {2}".format(cutoff.t3, cutoff.t3_delta, "slowing down" if cutoff.t3_d2 >= 0 else "")
    ])

    embed.add_field(name="Cutoffs", value=cutoff_content, inline=False)

    r = random.randint(25, 256)
    g = random.randint(25, 256)
    b = random.randint(25, 256)
    embed.colour = (r << 16) | (g << 8) | b

    return embed
