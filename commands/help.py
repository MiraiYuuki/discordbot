import loader
import config

@loader.command("help",
    description="Display commands' help messages.")
async def help(context, message, content):
    inspect_cmd = loader.ROOT_COMMAND

    for word in content.split():
        if word in inspect_cmd.sub_dispatch_table:
            inspect_cmd = inspect_cmd.sub_dispatch_table[word]
            break

        for cmd_struct in inspect_cmd.sub_dispatch_table.values():
            if word in cmd_struct.extwords:
                inspect_cmd = cmd_struct
                break
        else:
            continue

        break
    else:
        if content:
            return await context.reply("No such command: `{0}`.".format(content))

    context.arg0 = content
    await context.reply(inspect_cmd.help_message(context))

@loader.command("source", "code")
async def source(context, message, text):
    await context.reply(config.get("misc.source_repo_url",
        "My source code is not available at this time."))
