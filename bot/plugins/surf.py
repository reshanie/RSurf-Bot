import outlet
from outlet import errors, String
from furl import furl
import discord

from random import randrange

from functools import wraps


def check_private_server_link(url):
    url = furl(url)

    if url.host not in ("roblox.com", "www.roblox.com", "web.roblox.com"):  # check if link is to roblox
        return None

    url.host = "www.roblox.com"

    if not str(url.path).startswith("/games/272689493/"):  # check if link is to surf game
        return None

    if "privateServerLinkCode" not in url.args:  # check if link is for a private server
        return None

    if len(url.args["privateServerLinkCode"]) != 32:
        return None

    return str(url)


# decorators


def debug_only(func):
    if getattr(func, "is_command", False):
        raise SyntaxError("@debug_only decorator should be placed under the @command decorator")

    @wraps(func)
    async def new_func(self_, ctx, *args):
        if ctx.author.id != 231658954831298560:
            raise errors.MissingPermission("This is a debug command and can only be used by reshanie#7510")

        await func(self_, ctx, *args)

    return new_func


# plugin

# noinspection PyTypeChecker
class Plugin(outlet.Plugin):
    __plugin__ = "Private Servers"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        database = self.get_resource("database.py")

        self.db = database.Session()
        self.PrivateServer = database.PrivateServer

        self.private_server_channel = None

    async def on_ready(self):
        self.private_server_channel = self.bot.get_channel(376555570091524096)
        if self.private_server_channel:
            self.log.info("found private server channel")
        else:
            self.log.error("private server channel not found")

    @outlet.command("add-ps")
    async def add_private_server_command(self, ctx, url, *title):
        """Submit a private server for Surf to the <#376555570091524096> channel."""

        url = check_private_server_link(url)  # normalize URL

        if url is None:  # wasn't a link to surf private server
            raise errors.ArgumentError("The URL needs to be a link to a private server on Surf.")

        # check for duplicate

        ps = self.db.query(self.PrivateServer).filter_by(url=url)
        if ps.count() > 0:
            raise errors.ArgumentError("That private server is already in the list.")

        ps_id = randrange(100, 1000)  # random 3 digit server id

        try:

            embed = discord.Embed(title=" ".join(title) if title else None, description="{}".format(url),
                                  color=await self.bot.my_color(ctx.guild))

            embed.set_footer(text="Submitted by {}".format(ctx.author))

            msg = await self.private_server_channel.send(embed=embed)
        except Exception as e:
            self.log.error("error adding private server: {}".format(e))
        else:
            private_server = self.PrivateServer(id=ps_id, url=url, message_id=msg.id)

            self.db.add(private_server)  # add to db

            self.log.debug("committing db")
            self.db.commit()

            await msg.add_reaction("✅")
            await msg.add_reaction("❌")

            await ctx.message.delete()

            return "Private server added to list."

    async def on_message_delete(self, message):
        self.log.debug("message delete")

        ps = self.db.query(self.PrivateServer).filter_by(message_id=message.id).first()  # check if message is PS
        if ps:  # private server message was deleted
            self.log.info("Private server message was deleted from list")

            self.db.delete(ps)  # remove PS from database on delete

            self.log.debug("comitting db")
            self.db.commit()
