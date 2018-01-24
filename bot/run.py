from outlet import DiscordBot
import os

RSurfBot = DiscordBot(os.environ["RSURF_TOKEN"], "bot/plugins/",
                      "dev$" if os.environ.get("RSURF_DEV", None) else "$")

RSurfBot.run()
