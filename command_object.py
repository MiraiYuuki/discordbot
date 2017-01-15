import loader

class Command(object):
    def __init__(self, name, *shorthands, description=None, synopsis=None, examples=None, execution=None):
        self.word = name
        self.extwords = shorthands

        self.description = description
        self.synopsis = synopsis
        self.examples = examples

        self.sub_dispatch_table = {}

        self.execute = execution
        self.provider = loader.LOADING_MODULE

    def is_subcommand(self):
        return bool(self.sub_dispatch_table)

    def register_subcommand(self, name, *shorthands, description=None, synopsis=None, examples=None, execution=None):
        cmd = Command(name, *shorthands,
            description=description,
            synopsis=synopsis,
            examples=examples,
            execution=execution)
        self.sub_dispatch_table[name] = cmd
        return cmd

    def subcommand(self, name, *shorthands, description=None, synopsis=None, examples=None):
        def wrapper(f):
            cmd = self.register_subcommand(name, *shorthands, description=description, synopsis=synopsis, examples=examples, execution=f)
            return cmd
        return wrapper

    async def dispatch(self, context, message, effective_content):
        nargs = effective_content.split(maxsplit=1)

        if nargs:
            next_word = nargs.pop(0)
            next_ec = nargs.pop() if nargs else ""

            nc = self.sub_dispatch_table.get(next_word)

            if nc is None:
                for cmd_struct in self.sub_dispatch_table.values():
                    if next_word in cmd_struct.extwords:
                        nc = cmd_struct
                        break
        else:
            nc = None

        if nc is not None:
            context.push_arg0(next_word)

            await nc.dispatch(context, message, next_ec)
        elif self.execute:
            context.set_module(self.provider)
            print("dispatch: executing", message.content, "in", message.channel.name)
            await self.execute(context, message, effective_content)
        else:
            await self.default_implementation(context, message, effective_content)

    def __repr__(self):
        return "<Command '{0.word}' aka {0.extwords} :{0.sub_dispatch_table} from {0.provider}>".format(self)

    async def __call__(self, *args, **kwargs):
        return await self.execute(*args, **kwargs)

    @staticmethod
    async def noop_execute(context, message, content):
        return

    async def default_implementation(self, context, message, content):
        """ Reply with a help message. The content depends on whether you
            specified description, synopsis, examples, etc. """
        msg = []

        if self.description:
            if self.synopsis:
                msg.append("`{1} {0.synopsis}`: {0.description}\n".format(self, context.arg0))
            else:
                msg.append("`{1}`: {0.description}\n".format(self, context.arg0))
        elif not self.is_subcommand():
            msg.append("No help message available for this command.")

        if self.execute and self.examples:
            msg.append("**Examples**:")
            for eg in self.examples:
                msg.append("- `{0} {1} {2}`".format(context.arg0, self.word, eg))

        if self.is_subcommand():
            if self.word:
                msg.append("**Subcommands**:")
            else:
                msg.append("**Commands**:")

            for k in sorted(self.sub_dispatch_table.keys()):
                cmd_struct = self.sub_dispatch_table[k]

                st = "- {0} **{1}**".format(context.arg0, cmd_struct.word)
                if cmd_struct.synopsis:
                    st += " `{0}`".format(cmd_struct.synopsis)
                if cmd_struct.description:
                    st += ": {0}".format(cmd_struct.description)

                msg.append(st)

            if self.word:
                msg.append("\nFor further help on subcommands, DM me `help {0} [subcommand]`.".format(
                    self.word))
            else:
                msg.append("\nFor information about a specific command, DM me `help [command]`.")

        await context.reply("\n".join(msg))

class DefaultModuleContext(object):
    pass
