import loader
import discord
import sqlite3
import auth

P_SELFROLE_ADMIN = auth.declare_right("SELFROLE_ADMIN")
P_SELFROLE_USE = auth.declare_right("SELFROLE_USE")

class RoleNotFound(Exception):
    pass

@loader.context_class
class SelfRoleDB(object):
    def __init__(self):
        connection = sqlite3.connect("selfrole.db")
        connection.execute("""CREATE TABLE IF NOT EXISTS
            selfroles_v1 (
                server TEXT,
                name TEXT,
                role_id TEXT,
                mutual_exclusion_group INT
            )
        """)
        connection.commit()

        self.connection = connection

    def add_sar(self, server, role_id, name):
        self.connection.execute("INSERT INTO selfroles_v1 VALUES (?, ?, ?, ?)",
            (server, name, role_id, None))
        self.connection.commit()

    def remove_sar(self, server, role_id):
        self.connection.execute("DELETE FROM selfroles_v1 WHERE server=? AND role_id=?",
            (server, role_id))
        self.connection.commit()

    def find_role(self, server, name):
        cur = self.connection.execute("SELECT role_id FROM selfroles_v1 WHERE server=? AND name=?",
            (server, name)).fetchone()

        if cur is None:
            raise RoleNotFound(name)

        return cur[0]

ROLE_COMMAND = loader.register_command("role")

@ROLE_COMMAND.subcommand("make_not_self_assignable", "mnsa",
    description="Remove a role from the self-assignable list.",
    synopsis="[role name]")
@auth.requires_right(P_SELFROLE_ADMIN)
async def make_not_self_assignable(context, message, text):
    if not message.server:
        await context.reply("This command cannot be executed in a DM context.")

    if text.startswith("'"):
        the_role = discord.utils.get(message.server.roles, id=text.strip()[1:])
    else:
        the_role = discord.utils.get(message.server.roles, name=text.strip())

    context.remove_sar(message.server.id, the_role.id)
    await context.reply("OK.")

@ROLE_COMMAND.subcommand("make_self_assignable", "msa",
    description="Add a role to the self-assignable list.",
    synopsis="[role name]")
@auth.requires_right(P_SELFROLE_ADMIN)
async def make_self_assignable(context, message, text):
    if not message.server:
        await context.reply("This command cannot be executed in a DM context.")

    if text.startswith("'"):
        the_role = discord.utils.get(message.server.roles, id=text.strip()[1:])
    else:
        the_role = discord.utils.get(message.server.roles, name=text.strip())

    context.add_sar(message.server.id, the_role.id, the_role.name)
    await context.reply("OK.")

@ROLE_COMMAND.subcommand("add",
    description="Give yourself one or more roles (they must be from the self-assignable list).",
    synopsis="[role name], [more role names...]",
    examples=["Red, James Chungler", "Blue"])
@auth.requires_right(P_SELFROLE_USE)
async def addrole(context, message, text):
    rolenames = text.split(",")

    if not message.server:
        await context.reply("This command cannot be executed in a DM context.")

    add_roles = []
    try:
        for a_role in rolenames:
            id = context.find_role(message.server.id, a_role.strip())
            add_roles.append(discord.utils.get(message.server.roles, id=id))
    except RoleNotFound as offender:
        return await context.reply("Can't find role '{0}', or it is not assignable on this server.".format(str(offender)),
            mention=1)

    try:
        await context.client.add_roles(message.member, *add_roles)
    except discord.errors.Forbidden:
        await context.reply("Sorry, I can't assign roles on this server. "
            "If I should be able to and you are seeing this message, please let a server admin know.")
    else:
        await context.reply("OK, I've given you the requested roles.")

@ROLE_COMMAND.subcommand("del", "delete",
    description="Remove one or more roles from yourself (they must be from the self-assignable list).",
    synopsis="[role name], [more role names...]",
    examples=["Red, James Chungler", "Blue"])
@auth.requires_right(P_SELFROLE_USE)
async def delrole(context, message, text):
    rolenames = text.split(",")

    if not message.server:
        await context.reply("This command cannot be executed in a DM context.")

    edit_roles = []
    try:
        for a_role in rolenames:
            id = context.find_role(message.server.id, a_role.strip())
            edit_roles.append(discord.utils.get(message.server.roles, id=id))
    except RoleNotFound as offender:
        return await context.reply("Can't find role '{0}', or it is not assignable on this server.".format(str(offender)),
            mention=1)

    try:
        await context.client.remove_roles(message.member, *edit_roles)
    except discord.errors.Forbidden:
        await context.reply("Sorry, I can't remove roles on this server. "
            "If I should be able to and you are seeing this message, please let a server admin know.")
    else:
        await context.reply("OK, I've removed the requested roles from you.")

