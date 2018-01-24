import outlet
import discord


class Plugin(outlet.Plugin):
    __plugin__ = "Info"

    async def on_ready(self):
        game = discord.Game(name="RSurf Bot | $help")

        await self.bot.change_presence(game=game)
