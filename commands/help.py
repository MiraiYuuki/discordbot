import loader
import config

@loader.command("help",
    description="Display commands' help messages.")
async def help(context, message, content):
    inspect_cmd = loader.ROOT_COMMAND

    words = content.split()
    words.reverse()

    valid_words = []

    async def no_such_command(w):
        if valid_words:
            await context.reply("No such subcommand: `{0}` for `{1}`.".format(
                w, " ".join(valid_words)))
        else:
            await context.reply("No such command: `{0}`.".format(w))

    while words:
        w = words.pop()

        if w in inspect_cmd.sub_dispatch_table:
            inspect_cmd = inspect_cmd.sub_dispatch_table[w]
            valid_words.append(w)
            continue
        else:
            for child in inspect_cmd.sub_dispatch_table.values():
                if w in child.extwords:
                    inspect_cmd = child
                    valid_words.append(w)
                    break
            else:
                # no command
                return await no_such_command(w)

            # if we got here it means we found a command and broke
            # out of the inner for
            continue

    context.arg0 = content
    await context.reply(inspect_cmd.help_message(context))

@loader.command("source", "code")
async def source(context, message, text):
    await context.reply(config.get("misc.source_repo_url",
        "My source code is not available at this time."))
