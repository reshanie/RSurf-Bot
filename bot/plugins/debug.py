import time
from datetime import timedelta
from functools import wraps
import asyncio

import discord
import outlet
from outlet import errors

import psutil


def debug_only(func):
    if getattr(func, "is_command", False):
        raise SyntaxError("@debug_only decorator should be placed under the @command decorator")

    @wraps(func)
    async def new_func(self_, ctx, *args):
        if ctx.author.id != 231658954831298560:
            raise errors.MissingPermission("This is a debug command and can only be used by reshanie#7510")

        return await func(self_, ctx, *args)

    return new_func


# util

def tasks():
    return len([task for task in asyncio.Task.all_tasks() if not task.done()])


def sizeof_fmt(num, suffix='B'):
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return "%3.1f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f %s%s" % (num, 'Yi', suffix)


# plugin

class Plugin(outlet.Plugin):
    __plugin__ = "Debug"

    async def on_ready(self):
        self.start_time = time.time()

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
            result = repr(eval(expression))
            result = result.replace("```", "")

            return "```{}```".format(result)
        except Exception as e:
            return "{0.__class__.__name__}: ```{0!s}```".format(e)

    @outlet.command("status", "uptime")
    async def get_status(self, ctx):
        """Gets status of bot, including information such as uptime and number of tasks running."""

        uptime = timedelta(0, int(time.time() - self.start_time))

        embed = discord.Embed(color=await self.bot.my_color(ctx.guild))
        embed.add_field(name="Uptime", value=str(uptime))

        server_uptime = timedelta(0, int(time.time()) - int(psutil.boot_time()))

        embed.add_field(name="Server Uptime", value=str(server_uptime))

        embed.add_field(name="Running Tasks", value=str(tasks()))

        memory = psutil.virtual_memory()

        used = sizeof_fmt(memory.used)
        total = sizeof_fmt(memory.total)

        mem_string = "{} / {} used".format(used, total)

        embed.add_field(name="Memory", value=mem_string)

        await ctx.send(embed=embed)
