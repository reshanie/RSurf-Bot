import os
import outlet
from outlet import errors, Member
import discord

import keen

from functools import wraps

import time


# plugin

class Plugin(outlet.Plugin):
    __plugin__ = "Utilities"

    welcome = None
    member_role = None

    async def on_ready(self):
        game = discord.Game(name="RSurf Bot | $help")

        self.welcome = self.bot.get_channel(354117054422581258)  # get welcome channel
        self.member_role = discord.utils.get(self.welcome.guild.roles, id=353615956184006659)  # Surfer role

        await self.bot.change_presence(game=game)

        for guild in self.bot.guilds:
            me = guild.get_member(self.bot.user.id)

            if me:
                try:
                    await me.edit(nick="RSurf")
                except discord.errors.Forbidden:
                    pass

    async def get_roblox_username(self, user):
        self.log.debug("checking {} for roblox account".format(user))

        try:
            async with self.http.get("https://verify.eryn.io/api/user/{}".format(user.id)) as resp:
                r = await resp.json()

                return r.get("robloxUsername", None), r.get("robloxId", None)
        except:
            return None, None

    @outlet.command("roblox")
    @outlet.cooldown(3)
    async def roblox_cmd(self, ctx, user: Member):
        """Check if a user is verified with RoVerify, and if so send their Roblox username."""

        username, uid = await self.get_roblox_username(user)

        if username:
            return "{} is `{}` on Roblox.\n\nhttp://roblox.com/users/{}/profile".format(user, username, uid)
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

    # welcome channel

    unverified_join_msg = "Welcome to RSurf, {0.mention}. Please read <#421152883262619659> and <#353623771145306113>" \
                          " while an admin ranks you."
    verified_join_msg = "Welcome to RSurf, {0.mention}. Please read <#421152883262619659> and <#353623771145306113>"

    leave_msg = "**{0}** just slid off a ramp. **{0}** is now dead."

    async def on_member_join(self, member):
        if self.welcome is None:
            self.log.error("welcomejust"
                           "any surf maps channel not found")

        username, uid = await self.get_roblox_username(member)

        if username is None:
            await self.welcome.send(self.unverified_join_msg.format(member))
        else:
            await member.edit(roles=[self.member_role])

            await self.welcome.send(self.verified_join_msg.format(member))

    async def on_member_remove(self, member):
        if self.welcome is None:
            self.log.error("welcome channel not found")

        await self.welcome.send(self.leave_msg.format(member))
