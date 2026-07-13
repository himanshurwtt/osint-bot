import os
import logging
import traceback
from datetime import datetime, timezone
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bash = commands.Bot(command_prefix=".", intents=intents, help_command=None)
bash.launch_time = datetime.now(timezone.utc)  


discord.utils.setup_logging(level=logging.INFO)


@bash.event
async def on_ready():
    print(f"Logged in as {bash.user} (ID: {bash.user.id})")
    print("------")

    activity = discord.Activity(
        type=discord.ActivityType.listening,
        name="OSINT BOT | .help for commands",
    )
    await bash.change_presence(status=discord.Status.online, activity=activity)


@bash.event
async def on_command_error(ctx, error):
    print(f"\n=== ERROR in command '{ctx.command}' (invoked by {ctx.author}) ===")
    traceback.print_exception(type(error), error, error.__traceback__)


@bash.event
async def on_error(event, *args, **kwargs):
    print(f"\n=== UNHANDLED ERROR in event '{event}' ===")
    traceback.print_exc()


async def load_cogs():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            try:
                await bash.load_extension(f"cogs.{filename[:-3]}")
                print(f"Loaded cog: {filename}")
            except Exception:
                print(f"!!! FAILED to load cog: {filename}")
                traceback.print_exc()


async def main():
    if not DISCORD_TOKEN:
        raise SystemExit("DISCORD_TOKEN is missing — check your .env file.")

    async with bash:
        await load_cogs()
        await bash.start(DISCORD_TOKEN)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
