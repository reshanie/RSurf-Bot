import os
import outlet
from outlet import errors, Member
import discord

import keen

from functools import wraps

import time


# util decorators

def no_punished(func):
    if getattr(func, "is_command", False):
        raise SyntaxError("@debug_only decorator should be placed under the @command decorator")

    @wraps(func)
    async def new_func(self_, ctx, *args):
        if ctx.author.id != 231658954831298560:
            raise errors.MissingPermission("This is a debug command and can only be used by reshanie#7510")

        return await func(self_, ctx, *args)

    return new_func


# plugin

class Plugin(outlet.Plugin):
    __plugin__ = "Utilities"

    async def on_ready(self):
        game = discord.Game(name="RSurf Bot | $help")

        await self.bot.change_presence(game=game)

        for guild in self.bot.guilds:
            me = guild.get_member(self.bot.user.id)

            if me:
                try:
                    await me.edit(nick="RSurf")
                except discord.errors.Forbidden:
                    pass

    @outlet.command("roblox")
    @outlet.cooldown(3)
    async def get_roblox_username(self, ctx, user: Member):
        """Check if a user is verified with RoVerify, and if so send their Roblox username."""

        self.log.debug("checking {} for roblox account".format(user))

        async with self.http.get("https://verify.eryn.io/api/user/{}".format(user.id)) as resp:
            r = await resp.json()

            roblox_username = r.get("robloxUsername")
            if roblox_username:
                return "{} is `{}` on Roblox.\n\nhttp://roblox.com/users/{}/profile".format(user, roblox_username,
                                                                                            r["robloxId"])
            else:
                return "{} doesn't have a Roblox account in RoVerify's database.".format(user)

    @outlet.command("invite")
    async def invite(self, ctx):
        """Gets the permanent invite to the server."""

        if ctx.guild.id != 353615025589714946:
            return  # rsurf only

        return "http://discord.gg/th9DUhC"

    @outlet.command("user-info")
    async def user_info(self, ctx, *user: Member):
        """Gets info about a discord user."""

        if user:
            member = user[0]
        else:  # by default, use message author
            member = ctx.author

        embed = discord.Embed(color=await self.bot.my_color(ctx.guild))

        embed.set_author(name=str(member), icon_url=member.avatar_url)

        embed.add_field(name="Nickname", value=member.nick or member.name)

        embed.add_field(name="Account Created", value=str(member.created_at))
        embed.add_field(name="Joined " + ctx.guild.name, value=str(member.joined_at))

        embed.add_field(name="Top Role", value=member.top_role.name)

        await ctx.send(embed=embed)

    @outlet.command("embed-test")
    async def embed_test(self, ctx):
        embed = discord.Embed()

        for i in range(3):
            embed.add_field(name="h", value="h"*1500)

        await ctx.send(embed=embed)

    # @outlet.events.on_message()
    # async def report_event(self, message):
    #     if not os.environ.get("RSURF_DEV", False):
    #         self.log.debug("reporting message to keen")
    #
    #         keen.add_event("messages", {
    #             "id": message.id,
    #             "author": str(message.author),
    #             "channel": message.channel.name,
    #             "attachments": len(message.attachments)
    #         })
