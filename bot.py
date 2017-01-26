import discord
import asyncio
import config
import datetime
import re
import weakref
import auth
import json
import error_reporting
import asyncio
import sys
import os

def make_glue(c, f):
    async def glue(*a, **k):
        return await f(c, *a, **k)
    glue.__name__ = f.__name__
    return glue

def mention_needed_for(m):
    # commands without attention_char or @ are allowed in 1-to-1 DMs.
    if isinstance(m.channel, discord.PrivateChannel) and len(m.channel.recipients) == 1:
        return 0

    return 1

class SelfTerminate(BaseException):
    pass

class PersonalizedContext(object):
    """ The context object passed to command executors. """
    __slots__ = ("global_context", "client", "arg0", "message", "get_module_context", "_mc")

    def __init__(self, global_context, client, for_msg, get_module_context):
        self.global_context = global_context
        self.client = client
        self.message = for_msg
        self.get_module_context = get_module_context
        self.arg0 = ""
        self._mc = None

    # semi-private methods used by Command.dispatch

    def push_arg0(self, word):
        if self.arg0:
            self.arg0 = " ".join((self.arg0, word))
        else:
            self.arg0 = word

    def set_module(self, name):
        self._mc = self.global_context.module_contexts[name]

    # public methods, used by command executors

    def of(self, mod_name_or_global):
        """ Get the context of the named module, RELATIVE to the command package.
            Some names are special-cased, see DiscordBot.get_module_context. """
        return self.get_module_context(mod_name_or_global)

    async def reply(self, msg=None, *, embed=None, mention=0):
        if mention and msg:
            msg = " ".join((self.message.author.mention, msg))

        return await self.client.send_message(self.message.channel, msg, embed=embed)

    # for convenience, we proxy all other attributes to the module context

    def __getattr__(self, name):
        return getattr(self._mc, name)

    def __setattr__(self, name, value):
        if name not in self.__slots__:
            setattr(self._mc, name, value)
        else:
            super().__setattr__(name, value)

class DiscordBot(object):
    LATE_EVENTS = set()

    @classmethod
    def event(cls, f):
        cls.LATE_EVENTS.add(f)
        return f

    def __init__(self):
        self.client = discord.Client()
        self.late_reg_events(self.client)
        # the root command has no module, so add None to prevent KeyError
        self.module_contexts = {None: None}

        self.rights_db = auth.RightsDB(config.get("bot.rights_db_path", "rights.db"))
        self.log_db = error_reporting.LogDB(config.get("bot.error_log_db_path", "log.db"))

        # assigned in on_ready
        self.check_start_mention_regex = None
        self.is_ready = 0

    async def init_module(self, m):
        mctx = loader.get_context_class(m)()

        try:
            await mctx.init_with_context(self)
        except AttributeError:
            pass

        self.module_contexts[m.__name__] = mctx

    async def uninit_module(self, m):
        print("uninit_module: calling deinit on", m.__name__)

        try:
            await self.module_contexts[m.__name__].deinit(self)
        except AttributeError:
            pass

        del self.module_contexts[m.__name__]

    async def init_modules(self):
        for m in loader.LOADED_MODULES:
            await self.init_module(m)

    async def uninit_modules(self):
        for m in loader.LOADED_MODULES:
            await self.uninit_module(m)

    def get_module_context(self, mod_name_or_global):
        if mod_name_or_global == "discordbot":
            return self

        if mod_name_or_global == "auth":
            return self.rights_db

        return self.module_contexts[loader.fq_from_leaf(mod_name_or_global)]

    def late_reg_events(self, client):
        """ Bind handlers registered using @DiscordBot.event to
            the Client now that it has been allocated. """

        for func in DiscordBot.LATE_EVENTS:
            client.event(make_glue(self, func))

    async def init_modules_and_run_client(self, *args, **kwargs):
        await self.init_modules()
        await self.client.start(*args, **kwargs)

    def run(self, *args, **kwargs):
        loop = self.client.loop
        self.is_ready = 0

        try:
            loop.run_until_complete(self.init_modules_and_run_client(*args, **kwargs))
        except (KeyboardInterrupt, SelfTerminate):
            # https://github.com/Rapptz/discord.py/blob/async/discord/client.py#L522
            loop.run_until_complete(self.client.logout())
            pending = asyncio.Task.all_tasks(loop=loop)
            gathered = asyncio.gather(*pending, loop=loop)
            try:
                gathered.cancel()
                loop.run_until_complete(gathered)
                gathered.exception()
            except:
                pass
        finally:
            loop.run_until_complete(self.uninit_modules())
            loop.close()

    def restart(self):
        strat = config.get("bot.restart_strategy", "terminate")
        if strat == "terminate":
            self.terminate()
        elif strat == "reexec":
            os.execv(sys.executable, [sys.executable] + sys.argv)

    def terminate(self):
        def killer():
            print("terminate: DiscordBot will now exit. see you soon!")
            raise SelfTerminate()

        self.client.loop.call_soon(killer)

    # --x--

    def personalize(self, for_msg):
        return PersonalizedContext(self, self.client, for_msg, self.get_module_context)

@DiscordBot.event
async def on_ready(context):
    print("I'm", context.client.user.name, "#", context.client.user.id)
    print("Connected to Discord at", datetime.datetime.now())

    context.check_start_mention_regex = re.compile(r"<@!?{0}>".format(context.client.user.id))
    context.is_ready = 1

@DiscordBot.event
async def on_message(context, message):
    if message.author.bot or \
       message.channel.is_private and message.author.id == context.client.user.id or \
       not context.is_ready:
        return

    has_attention = 0
    cmd_start = 0

    ak = config.get("bot.attention_char", "=")
    match = context.check_start_mention_regex.match(message.content)
    if match:
        cmd_start = match.end(0)
        has_attention = 1
    elif message.content.startswith(ak):
        cmd_start = len(ak)
        has_attention = 1

    effective_content = message.content[cmd_start:].lstrip()

    # TODO: should allow the prefix to be used even in DMs
    if mention_needed_for(message) and not has_attention:
        return

    c_ctx = context.personalize(message)

    try:
        await loader.ROOT_COMMAND.dispatch(c_ctx, message, effective_content)
    except Exception as e:
        context.log_db.log_current_error(message, e)
        raise

if __name__ == '__main__':
    import loader
    loader.load_modules()

    mybot = DiscordBot()
    mybot.run(config.get("client.token"), bot=config.get("client.is_bot", True))
