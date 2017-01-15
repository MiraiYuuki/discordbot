import loader
import auth

P_INVITE = auth.declare_right("INVITE")

@loader.command("joinserver",
    description="Join the server from an instant invite link.",
    synopsis="[link]")
@auth.requires_right(P_INVITE)
async def joinserver(context, message, content):
    await context.client.accept_invite(content)

    try:
        await context.client.add_reaction(message, "\u2705")
    except discord.errors.Forbidden:
        await context.reply("\u2705")
