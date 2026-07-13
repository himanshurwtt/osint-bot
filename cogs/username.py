import asyncio
import aiohttp
import discord
from discord.ext import commands

EMBED_COLOR = discord.Color.from_rgb(57, 255, 20)

RESET = "\u001b[0m"
GREEN = "\u001b[1;32m"
CYAN = "\u001b[1;36m"
WHITE = "\u001b[1;37m"
YELLOW = "\u001b[1;33m"
RED = "\u001b[1;31m"
GREY = "\u001b[0;30m"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


PLATFORMS = {
    "GitHub": "https://github.com/{}",
    "GitLab": "https://gitlab.com/{}",
    "Reddit": "https://www.reddit.com/user/{}",
    "Twitter / X": "https://x.com/{}",
    "Instagram": "https://www.instagram.com/{}/",
    "TikTok": "https://www.tiktok.com/@{}",
    "YouTube": "https://www.youtube.com/@{}",
    "Twitch": "https://www.twitch.tv/{}",
    "Steam": "https://steamcommunity.com/id/{}",
    "Pinterest": "https://www.pinterest.com/{}/",
    "Spotify": "https://open.spotify.com/user/{}",
    "Telegram": "https://t.me/{}",
}


def ansi_block(lines: str) -> str:
    return f"```ansi\n{lines}\n```"


async def check_platform(session: aiohttp.ClientSession, name: str, url_template: str, username: str):
    url = url_template.format(username)
    try:
        async with session.get(
            url,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
            timeout=aiohttp.ClientTimeout(total=8),
        ) as resp:
            found = resp.status == 200
            return name, url, found, resp.status
    except Exception:
        return name, url, None, None  


async def scan_platforms(platforms: dict, username: str):
    async with aiohttp.ClientSession() as session:
        tasks = [
            check_platform(session, name, template, username)
            for name, template in platforms.items()
        ]
        return await asyncio.gather(*tasks)


class Username(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    
    @commands.command()
    async def username(self, ctx: commands.Context, name: str):
        async with ctx.typing():
            results = await scan_platforms(PLATFORMS, name)

            lines = f"{GREEN}root@osint-bot{RESET}:{CYAN}~/username{RESET}$ scan {name}\n\n"
            found_count = 0
            for platform_name, url, found, status in results:
                if found is None:
                    tag = f"{GREY}[ERROR]{RESET}"
                elif found:
                    tag = f"{GREEN}[FOUND]{RESET}"
                    found_count += 1
                else:
                    tag = f"{RED}[NOT FOUND]{RESET}"
                lines += f"{tag}  {WHITE}{platform_name:<14}{RESET} {CYAN}{url}{RESET}\n"

            lines += (
                f"\n{YELLOW}--- scan summary ---{RESET}\n"
                f"{WHITE}platforms checked: {len(PLATFORMS)}{RESET}\n"
                f"{WHITE}accounts found: {GREEN}{found_count}{RESET}"
            )

            embed = discord.Embed(
                title="🔎  USERNAME RECON",
                description=ansi_block(lines),
                color=EMBED_COLOR,
            )
            embed.add_field(
                name="⚠️ Note",
                value=(
                    "Some platforms block automated requests or always return `200`, "
                    "which can produce false positives/negatives. Always verify manually."
                ),
                inline=False,
            )
            embed.set_footer(
                text=f"Requested by {ctx.author}",
                icon_url=ctx.author.display_avatar.url,
            )
            await ctx.reply(embed=embed)

    
    @commands.command()
    async def namecheck(self, ctx: commands.Context, name: str):
        async with ctx.typing():
            results = await scan_platforms(PLATFORMS, name)

            lines = f"{GREEN}root@osint-bot{RESET}:{CYAN}~/username{RESET}$ quickcheck {name}\n\n"
            found_count = 0
            for platform_name, url, found, status in results:
                if found is None:
                    tag = f"{GREY}[ERROR]{RESET}"
                elif found:
                    tag = f"{GREEN}[TAKEN]{RESET}"
                    found_count += 1
                else:
                    tag = f"{RED}[AVAILABLE]{RESET}"
                lines += f"{tag}  {WHITE}{platform_name:<14}{RESET} {CYAN}{url}{RESET}\n"

            lines += (
                f"\n{YELLOW}--- scan summary ---{RESET}\n"
                f"{WHITE}platforms checked: {len(PLATFORMS)}{RESET}\n"
                f"{WHITE}accounts found: {GREEN}{found_count}{RESET}"
            )

            embed = discord.Embed(
                title="🔎  QUICK NAME CHECK",
                description=ansi_block(lines.rstrip()),
                color=EMBED_COLOR,
            )
            embed.set_footer(
                text=f"Requested by {ctx.author}",
                icon_url=ctx.author.display_avatar.url,
            )
            await ctx.reply(embed=embed)

    async def cog_command_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply(f"Usage: `.{ctx.command.name} <{error.param.name}>`")
        else:
            await ctx.reply(f"An error occurred: `{error}`")


async def setup(bot: commands.Bot):
    await bot.add_cog(Username(bot))