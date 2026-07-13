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


SOCIAL_PLATFORMS = {
    "Facebook": "https://www.facebook.com/{}",
    "Instagram": "https://www.instagram.com/{}/",
    "LinkedIn": "https://www.linkedin.com/in/{}",
    "Pinterest": "https://www.pinterest.com/{}/",
    "Threads": "https://www.threads.net/@{}",
    "Snapchat": "https://www.snapchat.com/add/{}",
    "Mastodon (mastodon.social)": "https://mastodon.social/@{}",
    "VK": "https://vk.com/{}",
    "Tumblr": "https://{}.tumblr.com",
    "Bluesky": "https://bsky.app/profile/{}.bsky.social",
    "Medium": "https://medium.com/@{}",
    "Quora": "https://www.quora.com/profile/{}",
}


def ansi_block(lines: str) -> str:
    return f"```ansi\n{lines}\n```"


async def check_platform(session: aiohttp.ClientSession, name: str, url_template: str, handle: str):
    url = url_template.format(handle)
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


async def scan_platforms(platforms: dict, handle: str):
    async with aiohttp.ClientSession() as session:
        tasks = [
            check_platform(session, name, template, handle)
            for name, template in platforms.items()
        ]
        return await asyncio.gather(*tasks)


def search_discord_members(bot: commands.Bot, handle: str, limit: int = 10):
    handle_lower = handle.lower()
    matches = []
    seen_ids = set()

    for member in bot.get_all_members():
        if member.id in seen_ids:
            continue
        name_fields = {member.name.lower(), (member.global_name or "").lower(), member.display_name.lower()}
        if handle_lower in name_fields or any(handle_lower in f for f in name_fields):
            matches.append((member, member.guild))
            seen_ids.add(member.id)
        if len(matches) >= limit:
            break

    return matches


class Social(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    
    @commands.command()
    async def social(self, ctx: commands.Context, handle: str):
        async with ctx.typing():
            results = await scan_platforms(SOCIAL_PLATFORMS, handle)

            lines = f"{GREEN}root@osint-bot{RESET}:{CYAN}~/social{RESET}$ scan {handle}\n\n"
            found_count = 0
            for platform_name, url, found, status in results:
                if found is None:
                    tag = f"{GREY}[ERROR]{RESET}"
                elif found:
                    tag = f"{GREEN}[FOUND]{RESET}"
                    found_count += 1
                else:
                    tag = f"{RED}[NOT FOUND]{RESET}"
                lines += f"{tag}  {WHITE}{platform_name:<28}{RESET} {CYAN}{url}{RESET}\n"

            lines += (
                f"\n{YELLOW}--- scan summary ---{RESET}\n"
                f"{WHITE}platforms checked: {len(SOCIAL_PLATFORMS)}{RESET}\n"
                f"{WHITE}profiles found: {GREEN}{found_count}{RESET}"
            )

            embed = discord.Embed(
                title="📱  SOCIAL MEDIA RECON",
                description=ansi_block(lines),
                color=EMBED_COLOR,
            )

            discord_matches = search_discord_members(self.bot, handle)
            discord_lines = f"{GREEN}root@osint-bot{RESET}:{CYAN}~/social{RESET}$ discord-lookup {handle}\n\n"
            if discord_matches:
                for member, guild in discord_matches:
                    discord_lines += (
                        f"{GREEN}[FOUND]{RESET}  {WHITE}{str(member):<28}{RESET} "
                        f"{GREY}└─ shared in{RESET} {CYAN}{guild.name}{RESET}\n"
                    )
                discord_lines += (
                    f"\n{YELLOW}--- lookup summary ---{RESET}\n"
                    f"{WHITE}matches found: {GREEN}{len(discord_matches)}{RESET}"
                )
            else:
                discord_lines += (
                    f"{RED}[NOT FOUND]{RESET}  {WHITE}no match in shared servers{RESET}\n\n"
                    f"{GREY}Discord has no public profile-by-username page, so this only{RESET}\n"
                    f"{GREY}checks servers this bot is already a member of — not Discord{RESET}\n"
                    f"{GREY}as a whole.{RESET}"
                )

            embed.add_field(
                name="💬 Discord (shared servers only)",
                value=ansi_block(discord_lines.rstrip()),
                inline=False,
            )

            embed.add_field(
                name="⚠️ Note",
                value=(
                    "Many platforms block automated requests, require login to view "
                    "profiles, or always return `200` regardless of whether the handle "
                    "exists — this can produce false positives/negatives. Treat results "
                    "as leads to verify manually, not confirmed matches. This only checks "
                    "whether a profile URL resolves — it does not confirm the account "
                    "belongs to any specific person."
                ),
                inline=False,
            )
            embed.set_footer(
                text=f"Requested by {ctx.author}",
                icon_url=ctx.author.display_avatar.url,
            )
            await ctx.reply(embed=embed)

    async def cog_command_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply(f"Usage: `.{ctx.command.name} <name_or_handle>`")
        else:
            await ctx.reply(f"An error occurred: `{error}`")


async def setup(bot: commands.Bot):
    await bot.add_cog(Social(bot))
