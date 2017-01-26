import sqlite3
import discord.errors
from collections import namedtuple
from functools import partial

# The set of rights declared with declare_right. You can
# use it to check for spelling errors, e.g.
# if user_string not in KNOWN_PERMISSION_FLAGS: raise ValueError("oops!")
KNOWN_PERMISSION_FLAGS = set()

# Lower = higher priority. Pass these to RightsDB.write_permission.
SCOPE_USER    = 100
SCOPE_ROLE    = 200
SCOPE_CHANNEL = 250
SCOPE_SERVER  = 300

# A right.
flag_t = namedtuple("flag_t", ("name",))
grant_t = namedtuple("grant_t", ("scope", "subject", "right", "permitted"))

def declare_right(name):
    KNOWN_PERMISSION_FLAGS.add(name)
    return flag_t(name)

class RightsDB(object):
    def __init__(self, path):
        connection = sqlite3.connect(path)
        connection.execute("""CREATE TABLE IF NOT EXISTS
            effective_permission (
                _type INT,
                _flagname TEXT,
                _userid_or_group TEXT,
                _have INT
            )
        """)
        connection.commit()

        self.connection = connection

    def write_permission(self, type_, subject, flag, value):
        k = self.connection.execute("SELECT _have FROM effective_permission WHERE _flagname = ? AND _userid_or_group = ? AND _type = ?", (flag.name, subject, type_)).fetchone()

        if k is None:
            self.connection.execute("INSERT INTO effective_permission VALUES (?, ?, ?, ?)", (type_, flag.name, subject, value))
        else:
            self.connection.execute("UPDATE effective_permission SET _have = ? WHERE _flagname = ? AND _userid_or_group = ? AND _type = ?", (value, flag.name, subject, type_))

        self.connection.commit()

    def evaluate(self, server_id, channel_id, role_ids, user_id, flag):
        """ Check whether the message has the given right (from declare_right).
            Checks based on server, channel, roles, user ID in ascending order of
            priority. """

        joined = ",".join(repr(k) for k in role_ids)

        the_query = ("SELECT _have FROM effective_permission "
            "WHERE _flagname = ? AND ( "
            "    (_type = 300 AND _userid_or_group = ?) OR "
            "    (_type = 250 AND _userid_or_group = ?) OR "
            "    (_type = 200 AND _userid_or_group IN ({0})) OR "
            "    (_type = 100 AND _userid_or_group = ?) "
            ") ORDER BY _type").format(joined)

        k = self.connection.execute(the_query, (flag.name, server_id, channel_id, user_id))

        perm = k.fetchone()
        if perm is not None:
            return perm[0]

        return 0

    def list_applicable(self, server_id, channel_id, role_ids, user_id):
        joined = ",".join(repr(k) for k in role_ids)

        the_query = ("SELECT _type, _flagname, _userid_or_group, _have FROM effective_permission "
            "WHERE ( "
            "    (_type = 300 AND _userid_or_group = ?) OR "
            "    (_type = 250 AND _userid_or_group = ?) OR "
            "    (_type = 200 AND _userid_or_group IN ({0})) OR "
            "    (_type = 100 AND _userid_or_group = ?) "
            ") ORDER BY _type").format(joined)

        k = self.connection.execute(the_query, (server_id, channel_id, user_id))
        return [grant_t(scope, subject, flag_t(right), pm) for scope, right, subject, pm in k]

async def evaluate_access_wrapper(execute, flag, context, message, content):
    rightsdb = context.of("auth")

    if message.channel.is_private:
        server_id = None
    else:
        server_id = message.server.id

    if isinstance(message.author, discord.Member):
        roles = [role.id for role in message.author.roles]
    else:
        roles = []

    if not rightsdb.evaluate(server_id, message.channel.id, roles, message.author.id, flag):
        try:
            await context.client.add_reaction(message, "🚫")
        except discord.errors.Forbidden:
            await context.reply("{1} You need the {0} right to perform this command, nya.".format(
                flag.name,
                message.author.mention
            ))
    else:
        await execute(context, message, content)

def requires_right(flag):
    """ Returns a decorator for command executors.
        Checks that the user has the given flag (from declare_right), then
        calls through to the executor.

        See evaluate_access_wrapper. """

    def wrapper(exec_):
        return partial(evaluate_access_wrapper, exec_, flag)

    return wrapper
