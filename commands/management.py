import loader
import auth
import traceback
import sys
import config
import json
import discord
import os
import binascii

P_MANAGE_CONFIG = auth.declare_right("MANAGE_CONFIG")
P_MANAGE_MODULES = auth.declare_right("MANAGE_MODULES")
P_EVAL_CODE = auth.declare_right("EVAL_CODE")

mod = loader.register_command("mod", "m",
    description="Load, reload, and unload command modules.")

@mod.subcommand("reload",
    description="Reload a module.")
@auth.requires_right(P_MANAGE_MODULES)
async def reload_mod(context, message, content):
    fq = loader.fq_from_leaf(content)

    if fq not in sys.modules:
        return await context.reply("It's not loaded, nya.")

    bot = context.of("discordbot")

    mod = sys.modules[fq]
    loader.unload_module(content)
    await bot.uninit_module(mod)
    del mod

    try:
        mod = loader.load_module(content)
        await bot.init_module(mod)
    except Exception as e:
        await context.reply("Loading '{0}' failed with a {1}. Fix it and `load` the module again.".format(
            content, e.__class__.__name__))
        raise
    else:
        await context.reply("\u2705")

@mod.subcommand("unload",
    description="Unload a module.")
@auth.requires_right(P_MANAGE_MODULES)
async def unload_mod(context, message, content):
    fq = loader.fq_from_leaf(content)

    if fq not in sys.modules:
        return await context.reply("It's not loaded, nya.")

    bot = context.of("discordbot")
    mod = sys.modules[fq]
    loader.unload_module(content)
    await bot.uninit_module(mod)
    del mod

    await context.reply("\u2705")

@mod.subcommand("load",
    description="Load a module.")
@auth.requires_right(P_MANAGE_MODULES)
async def load_mod(context, message, content):
    fq = loader.fq_from_leaf(content)

    if fq in sys.modules:
        return await context.reply("It's already loaded, nya.")

    bot = context.of("discordbot")

    try:
        mod = loader.load_module(content)
        await bot.init_module(mod)
    except Exception as e:
        await context.reply("Loading '{0}' failed with a {1}. Fix it and `load` the module again.".format(
            content, e.__class__.__name__))
        raise
    else:
        await context.reply("\u2705")

@loader.command("eval",
    description="Executes Python code in command handler context.")
@auth.requires_right(P_EVAL_CODE)
async def eval_code(context, message, content):
    f_name = binascii.hexlify(os.urandom(16)).decode("ascii")
    code = "async def _{0}(context, message, content): return {1}".format(
        f_name,
        content
    )
    print(code)
    exec(code)

    k = eval("_{0}(context, message, content)".format(f_name))
    await context.reply(str(await k))

config_command = loader.register_command("config", "cf",
    description="Write configuration variables.")
sensitive_keys = {"client.token"}

@config_command.subcommand("write", "w")
@auth.requires_right(P_MANAGE_CONFIG)
async def config_write(context, message, text):
    args = text.split(maxsplit=1)
    if len(args) != 2:
        return await context.reply("A value must be specified.")

    key, value = args

    if key in sensitive_keys:
        return await context.reply("The key '{0}' is too important to be written from Discord. Please update configuration.db manually.".format(key))

    try:
        json.loads(value)
    except ValueError:
        return await context.reply("The content is not valid JSON.")

    config.write_direct(key, value)

    try:
        await context.client.add_reaction(message, "\u2705")
    except discord.errors.Forbidden:
        await context.reply("\u2705")
