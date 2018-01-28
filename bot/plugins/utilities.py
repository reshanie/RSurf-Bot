import outlet
from outlet import errors, Member
import discord


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

    async def on_member_join(self, member):
        if member.guild.id == 353615025589714946:  # only rsurf
            self.log.info("{} joined RSurf. Giving surfer role".format(member))

            surfer_role = discord.utils.get(member.guild.roles, name="Surfer")

            if surfer_role is None:
                self.log.error("surfer role not found")
                raise Exception("surfer role not found")

            await member.add_roles(surfer_role)

    # @outlet.command("dd")
    # async def dd(self, ctx, id: Number):
    #     if ctx.author.id != 231658954831298560:
    #         return
    #
    #     await ctx.message.delete()
    #
    #     msg = await ctx.channel.get_message(id)
    #
    #     if msg is not None:
    #         await msg.delete()

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

        channel = discord.utils.get(ctx.guild.channels, name="rules") \
                  or discord.utils.get(ctx.guild.channels, name="general") \
                  or discord.utils.get(ctx.guild.channels, name="main")

        if not channel:
            raise errors.ArgumentError("Invite channel not found.")

        invite = await channel.create_invite(unique=False)

        return str(invite)

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
        embed.add_field(name="Joined "+ctx.guild.name, value=str(member.joined_at))

        embed.add_field(name="Top Role", value=member.top_role.name)

        await ctx.send(embed=embed)