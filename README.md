## discordbot

It's a Discord bot!
If you want to play with a running instance of the bot, Miku-nya#7061 is in
the Starlight Stage Discord server.

### virtualenv and dependencies...

```
python3 -m venv rt
source rt/bin/activate
pip3 install -r requirements.txt
```

### Initial configuration

First give your bot a token by writing the "client.token" config key.
If you're using a regular user token, write "client.is_bot" to False too.

```
(rt) λ python3
Python 3.5.2 (default, Jul 28 2016, 21:28:00)
[GCC 4.2.1 Compatible Apple LLVM 7.3.0 (clang-703.0.31)] on darwin
Type "help", "copyright", "credits" or "license" for more information.
>>> import config
config: connecting
>>> config.write("client.token", "blah...")
>>> config.write("client.is_bot", False)
```

Then you should give yourself the `MANAGE_PERMISSIONS` right.

```
python3 initrights.py [my user id]
```

Now you can run bot.py.

### Adding commands

Create a new file for your command(s) in the commands directory.

```python
async def say_hello(context, message, text):
    await context.reply("hello " + message.author.name)
```

-----

To add it to the command tree, use the loader.command decorator.

```python
import loader

@loader.command("hello")
async def say_hello(context, message, text):
    await context.reply("hello " + message.author.name)
```

Users can now invoke your command by saying `@botname#1234 hello`.

-----

You may want to require that users have a specific right to run your
command. For that, we have the auth.requires_right decorator.

Note that requires_right goes below all loader.command decorations.

```python
import loader
import auth

P_CAN_SAY_HELLO = auth.declare_right("P_CAN_SAY_HELLO")

@loader.command("hello")
@auth.requires_right(P_CAN_SAY_HELLO)
async def say_hello(context, message, text):
    await context.reply("hello " + message.author.name)
```

-----

You may want to add a subcommand to an existing command.

```python
import loader
import auth

P_CAN_SAY_HELLO = auth.declare_right("P_CAN_SAY_HELLO")

@loader.command("hello")
@auth.requires_right(P_CAN_SAY_HELLO)
async def say_hello(context, message, text):
    await context.reply("hello " + message.author.name)

@say_hello.subcommand("world")
async def say_hello_world(context, message, text):
    await context.reply("hello world!")
```

Now, if `Bob` says `@botname#1234 hello`, it will reply `hello Bob`,
but if he says `@botname#1234 hello world`, it will reply `hello world!`

Also, note that we didn't decorate `say_hello_world` with
`@auth.requires_right(P_CAN_SAY_HELLO)`. Anyone will be able to
run `@botname#1234 hello world`, unless you decorate it again.

-----

You may want to create a stub command that does nothing and make
your real commands subcommands of it (like the deresute module does).
The loader.register_command function creates stub commands.

```python
import loader
import auth

P_CAN_SAY_HELLO = auth.declare_right("P_CAN_SAY_HELLO")

hello_stub = loader.register_command("hello")

@hello_stub.subcommand("me")
@auth.requires_right(P_CAN_SAY_HELLO)
async def say_hello(context, message, text):
    await context.reply("hello " + message.author.name)

@hello_stub.subcommand("world")
async def say_hello_world(context, message, text):
    await context.reply("hello world!")
```

-----

You will eventually need to share some state between executions of your
commands. The loader.context_class decorator on a class will make a shared
instance of it available to all commands in the module.

```python
import loader
import auth

P_CAN_SAY_HELLO = auth.declare_right("P_CAN_SAY_HELLO")

@loader.context_class
class ModState(object):
    def __init__(self):
        self.last_helloed = "nobody"

hello_stub = loader.register_command("hello")

@hello_stub.subcommand("me")
@auth.requires_right(P_CAN_SAY_HELLO)
async def say_hello(context, message, text):
    await context.reply("hello " + message.author.name)
    context.last_helloed = message.author.name

@hello_stub.subcommand("world")
async def say_hello_world(context, message, text):
    await context.reply("hello world!")

@hello_stub.subcommand("last")
async def who_said_hello_last(context, message, text):
    await context.reply("I last said hello to " + context.last_helloed)
```

There's probably more stuff hiding in the code.

The underlying discord.Client is also available as context.client,
so you can access the full discord API.
