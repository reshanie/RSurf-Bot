import time
from functools import wraps

import discord
import outlet
from outlet import errors


def debug_only(func):
    if getattr(func, "is_command", False):
        raise SyntaxError("@debug_only decorator should be placed under the @command decorator")

    @wraps(func)
    async def new_func(self_, ctx, *args):
        if ctx.author.id != 231658954831298560:
            raise errors.MissingPermission("This is a debug command and can only be used by reshanie#7510")

        return await func(self_, ctx, *args)

    return new_func


# util decorators


# plugin

class Plugin(outlet.Plugin):
    __plugin__ = "Debug"

    @outlet.command("ping")
    async def ping(self, ctx):
        """Get ping time."""
        start = time.time()
        msg = await ctx.channel.send("Pong!")
        send_time = time.time() - start

        latency = self.bot.latency

        embed = discord.Embed(color=await self.bot.my_color(ctx.guild))
        embed.set_author(name="🏓 Pong!")

        embed.add_field(name="API", value="{0:.01f}ms".format(send_time * 1000))
        embed.add_field(name="Latency", value="{0:.01f}ms".format(latency * 1000))

        await msg.edit(content="", embed=embed)

    @outlet.command("eval")
    @debug_only
    async def eval_command(self, ctx, *expression):
        expression = ctx.message.clean_content

        expression = expression[expression.find(" "):]

        try:
            return repr(eval(expression))
        except Exception as e:
            return "{0.__class__.__name__}: {0!s}".format(e)
