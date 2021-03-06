import loader
import auth
import shlex
import re
import discord

P_MANAGE_PERMISSIONS = auth.declare_right("MANAGE_PERMISSIONS")

SCOPE_CHAR = {
    "u": auth.SCOPE_USER,
    "r": auth.SCOPE_ROLE,
    "c": auth.SCOPE_CHANNEL,
    "s": auth.SCOPE_SERVER,
}
mention_regex = re.compile("<(@|#)!?([0-9]+)>")

@loader.command("grant",
    description="Give flags to a specific user, role, or the entire server.",
    synopsis="['server | #channel | @user] flag ...",
    examples=["'server MANAGE_PERMISSIONS", "@Miku-nya#7061 DEBUG_COMMAND"])
@auth.requires_right(P_MANAGE_PERMISSIONS)
async def grant(context, message, content, check_flag=1):
    args = content.split()

    if len(args) < 2:
        return await context.reply("You must provide a target and a list of rights.")

    target = args.pop(0)

    scope = None
    subject = None

    if target == "'server":
        scope = auth.SCOPE_SERVER
        subject = message.server.id
    elif target.startswith("~"):
        scope = SCOPE_CHAR.get(target[1], None)

        if scope is None:
            return await context.reply("The scope is invalid.")

        subject = target[2:]
    else:
        match = mention_regex.match(target)
        if match:
            scope = auth.SCOPE_USER if match.group(1) == "@" else auth.SCOPE_CHANNEL
            subject = match.group(2)

    if not (scope and subject):
        return await context.reply("Grant target invalid, nya.")

    for flagname in args:
        if flagname.startswith("-"):
            have = 0
            flagname = flagname[1:]
        else:
            have = 1

        if check_flag and flagname not in auth.KNOWN_PERMISSION_FLAGS:
            return await context.reply("Undeclared right, {0}.".format(
                flagname, content))

        context.of("auth").write_permission(scope, subject, auth.declare_right(flagname), have)

    try:
        await context.client.add_reaction(message, "\u2705")
    except discord.errors.Forbidden:
        await context.reply("\u2705", mention=1)

@loader.command("uid",
    description="Tells you what your user ID is.")
async def whoami(context, message, content):
    await context.client.send_message(message.channel,
        "{0} {1}".format(message.author.mention, message.author.id))

@loader.command("lsrole",
    description="List server roles.")
@auth.requires_right(P_MANAGE_PERMISSIONS)
async def lsrole(context, message, content):
    targ = discord.utils.find(lambda s: s.id == content, context.client.servers)

    for k in targ.roles:
        await context.reply("{0} -> {1}".format(k.name, k.id))
