from outlet import DiscordBot
import os

RSurfBot = DiscordBot(os.environ["RSURF_TOKEN"],
                      plugin_dir="bot/plugins/", resource_dir="bot/resources",
                      prefix="dev$" if os.environ.get("RSURF_DEV", None) else "$")

RSurfBot.run()
