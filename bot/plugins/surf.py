import outlet
from outlet import errors, String
from furl import furl
import discord

from random import randrange

from functools import wraps


def check_private_server_link(url):
    url = furl(url)

    if url.host not in ("roblox.com", "www.roblox.com", "web.roblox.com"):  # check if link is to roblox
        return False

    url.host = "www.roblox.com"

    if not str(url.path).startswith("/games/272689493/"):  # check if link is to surf game
        return False

    if "privateServerLinkCode" not in url.args:  # check if link is for a private server
        return False

    return True


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
    __plugin__ = "Surf"

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
            self.log.error("private esrver channel not found")

    @outlet.command("add-ps")
    async def add_private_server_command(self, ctx, url, *title):
        """Submit a private server for Surf to the <#376555570091524096> channel."""

        if not check_private_server_link(url):
            raise errors.ArgumentError("The URL needs to be a link to a private server on Surf.")

        ps_id = randrange(100, 1000)

        try:

            embed = discord.Embed(title=" ".join(title) if title else None, description="{}".format(url),
                                  color=await self.bot.my_color(ctx.guild))

            embed.set_footer(text="Submitted by {}".format(ctx.author))

            msg = await self.private_server_channel.send(embed=embed)
        except Exception as e:
            self.log.error("error adding private server: {}".format(e))
        else:
            private_server = self.PrivateServer(id=ps_id, url=url, message_id=msg.id)

            self.db.add(private_server)

            self.log.debug("committing db")
            self.db.commit()

            await msg.add_reaction("✅")
            await msg.add_reaction("❌")

            await ctx.send("Private server added to list.")
            await ctx.message.delete()

    async def on_message_delete(self, message):
        self.log.debug("message delete")

        ps = self.db.query(self.PrivateServer).filter_by(message_id=message.id).first()
        if ps:  # private server message was deleted
            self.log.info("Private server message was deleted from list")

            self.db.delete(ps)

            self.log.debug("comitting db")
            self.db.commit()
