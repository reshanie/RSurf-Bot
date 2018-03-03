import random
from functools import wraps
import asyncio

import outlet


# decorators

def disable_in_main(func):
    if getattr(func, "is_command", False):
        raise SyntaxError("@disable_in_main decorator should be placed under the @command decorator")

    @wraps(func)
    async def new_func(self_, ctx, *args):
        if ctx.channel.name in ("general", "main"):
            await ctx.message.delete()

            msg = await ctx.channel.send("This command can't be used in the main channel.")

            await asyncio.sleep(5)
            await msg.delete()

            return

        return await func(self_, ctx, *args)

    return new_func


# plugin

# noinspection PyTypeChecker
class Plugin(outlet.Plugin):
    __plugin__ = "Fun"

    @outlet.command("roll")
    # @disable_in_main
    async def roll(self, ctx, *text):
        """Rolls a number from 1 - 100."""

        return str(random.randint(1, 100))

    @outlet.command("8ball")
    # @disable_in_main
    async def magic_8ball(self, ctx, *text):
        """Let the 8ball decide your fate."""

        return "🎱 " + random.choice([
            "It is certain", "As I see it, yes", "It is decidedly so", "Most likely", "Without a doubt", "Outlook good",
            "Yes definitely", "Yes", "You may rely on it", "Signs point to yes", "Reply hazy try again",
            "Ask again later", "Better not tell you now", "Cannot predict now", "Concentrate and try again",
            "Don't count on it", "My reply is no", "My sources say no", "Outlook is not so good", "Very doubtful"
        ]) + " 🎱"

    @outlet.command("coinflip")
    # @disable_in_main
    async def coinflip(self, ctx):
        """Flip a coin!"""

        return random.choice(("Heads", "Tails"))
