from outlet import DiscordBot
import os

RSurfBot = DiscordBot(os.environ["RSURF_TOKEN"], "plugins/",
                      "$")

RSurfBot.run()
