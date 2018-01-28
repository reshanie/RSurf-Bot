import outlet
from outlet import Number
import random


# decorators


# plugin

# noinspection PyTypeChecker
class Plugin(outlet.Plugin):
    __plugin__ = "Fun"

    @outlet.command("roll")
    async def roll(self, ctx, *text):
        """Rolls a number from 1 - 100."""

        return str(random.randint(1, 100))

    @outlet.command("8ball")
    async def magic_8ball(self, ctx, *text):
        """Let the 8ball decide your fate."""

        return random.choice([
            "It is certain", "As I see it, yes", "It is decidedly so", "Most likely", "Without a doubt", "Outlook good",
            "Yes definitely", "Yes", "You may rely on it", "Signs point to yes", "Reply hazy try again",
            "Ask again later", "Better not tell you now", "Cannot predict now", "Concentrate and try again",
            "Don't count on it", "My reply is no", "My sources say no", "Outlook is not so good", "Very doubtful"
        ])

    @outlet.command("coinflip")
    async def coinflip(self, ctx):
        """Flip a coin!"""

        return random.choice(("Heads", "Tails"))
