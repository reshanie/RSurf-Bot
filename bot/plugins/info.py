import outlet
import discord


class Plugin(outlet.Plugin):
    __plugin__ = "Info"

    async def on_ready(self):
        game = discord.Game(name="prefix = $")

        await self.bot.change_presence(game=game)

    @outlet.command("info")
    async def info_command(self, ctx):
        await ctx.send("suck nut ur mum gay")
