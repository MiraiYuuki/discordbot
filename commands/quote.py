import loader
import config
import sqlite3
import auth

P_MANAGE_QUOTE = auth.declare_right("MANAGE_QUOTE")

class QuoteAlreadyExistsError(Exception):
    pass

@loader.context_class
class QuoteDB(object):
    def __init__(self):
        connection = sqlite3.connect("quotes.db")
        connection.execute("""CREATE TABLE IF NOT EXISTS
            quotes_v1 (
                _command TEXT,
                _originator TEXT,
                _response TEXT
            )
        """)
        connection.commit()

        self.connection = connection

    async def init_with_context(self, bot):
        print("init_with_context")
        for name in self.quote_names():
            print("register stub", name)
            loader.register_command(name, execution=quote_command, hide=1)

    async def deinit(self, bot):
        for name in self.quote_names():
            print("unregister stub", name)
            loader.delete_command(name)

    def quote_names(self):
        k = self.connection.execute("SELECT _command FROM quotes_v1")
        return [na for na, in k.fetchall()]

    def set_quote_for_name(self, name, response, originator):
        name = name.lower()

        if self.get_quote_for_name(name):
            raise QuoteAlreadyExistsError()

        self.connection.execute("INSERT INTO quotes_v1 VALUES (?, ?, ?)", (name, originator, response))
        self.connection.commit()

        loader.register_command(name, execution=quote_command, hide=1)

    def delete_quote(self, name):
        name = name.lower()

        self.connection.execute("DELETE FROM quotes_v1 WHERE _command = ?", (name,))
        self.connection.commit()

        loader.delete_command(name)

    def get_quote_for_name(self, name):
        name = name.lower()

        k = self.connection.execute("SELECT _response FROM quotes_v1 WHERE _command = ?", (name,)).fetchone()

        if k is None:
            return None
        else:
            return k[0]

async def quote_command(context, message, content):
    response = context.of(loader.localname(__name__)).get_quote_for_name(context.arg0)

    if response:
        await context.reply(response)
    else:
        print("quote_command: bug: {0} bound but not defined".format(context.arg0))

manage_quote = loader.register_command("quote",
    description="Manage quotes.")

@manage_quote.subcommand("add")
@auth.requires_right(P_MANAGE_QUOTE)
async def add_quote(context, message, content):
    args = content.split(maxsplit=1)

    if len(args) != 2:
        return await context.reply("usage: add_quote [command] [response...]", mention=1)

    try:
        context.set_quote_for_name(args[0], args[1], message.author.id)
        await context.reply("Added '{0}'.".format(args[0]), mention=1)
    except QuoteAlreadyExistsError:
        return await context.reply("That quote already exists. Delete it first.", mention=1)

@manage_quote.subcommand("delete")
@auth.requires_right(P_MANAGE_QUOTE)
async def del_quote(context, message, content):
    context.delete_quote(content)
    await context.reply("Quote was deleted (if it existed).", mention=1)

@manage_quote.subcommand("list")
@auth.requires_right(P_MANAGE_QUOTE)
async def list_quote(context, message, content):
    context.delete_quote(content)
    await context.reply("Available: `{0}`".format(" ".join(context.quote_names())), mention=1)
