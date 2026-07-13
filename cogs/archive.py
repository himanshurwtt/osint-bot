import os
import discord
from discord.ext import commands
import aiohttp

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


def ansi_block(lines: str) -> str:
    return f"```ansi\n{lines}\n```"


def kv(key: str, value: str) -> str:
    return f"{CYAN}{key}{RESET}: {WHITE}{value}{RESET}"


class Archive(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    
    @commands.command()
    async def wayback(self, ctx: commands.Context, url: str):
        async with ctx.typing():
            if not url.startswith(("http://", "https://")):
                url = "https://" + url

            cdx_url = (
                "http://web.archive.org/cdx/server/cdx"
                f"?url={url}&output=json&fl=timestamp&collapse=digest&limit=100000"
            )
            available_url = f"https://archive.org/wayback/available?url={url}"

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        cdx_url,
                        headers={"User-Agent": USER_AGENT},
                        timeout=aiohttp.ClientTimeout(total=15),
                    ) as resp:
                        cdx_data = await resp.json() if resp.status == 200 else []

                    async with session.get(
                        available_url,
                        headers={"User-Agent": USER_AGENT},
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as resp:
                        available_data = await resp.json() if resp.status == 200 else {}
            except Exception as e:
                await ctx.reply(f"Couldn't reach the Wayback Machine: `{e}`")
                return

            timestamps = [row[0] for row in cdx_data[1:]] if len(cdx_data) > 1 else []

            if not timestamps:
                await ctx.reply(f"No Wayback Machine snapshots found for `{url}`.")
                return

            def fmt_ts(ts: str) -> str:
                return f"{ts[0:4]}-{ts[4:6]}-{ts[6:8]}"

            first_ts = timestamps[0]
            last_ts = timestamps[-1]

            snapshot = available_data.get("archived_snapshots", {}).get("closest", {})
            latest_url = snapshot.get("url", f"https://web.archive.org/web/{last_ts}/{url}")

            lines = f"{GREEN}root@osint-bot{RESET}:{CYAN}~/archive{RESET}$ wayback {url}\n\n"
            lines += kv("total_snapshots", str(len(timestamps))) + "\n"
            lines += kv("first_seen", fmt_ts(first_ts)) + "\n"
            lines += kv("last_seen", fmt_ts(last_ts)) + "\n"
            lines += kv("latest_snapshot", latest_url)

            embed = discord.Embed(
                title="🗄️  WAYBACK MACHINE",
                description=f"**Snapshot history for ({url})**\n\n{ansi_block(lines)}",
                color=EMBED_COLOR,
            )
            embed.set_footer(
                text=f"Requested by {ctx.author} • data via web.archive.org",
                icon_url=ctx.author.display_avatar.url,
            )
            await ctx.reply(embed=embed)

    
    @commands.command()
    async def pastesearch(self, ctx: commands.Context, keyword: str):
        async with ctx.typing():
            api_key = os.getenv("RAPIDAPI_KEY")

            if not api_key:
                embed = discord.Embed(
                    title="🗄️  PASTE DUMP SEARCH",
                    description=ansi_block(
                        f"{GREEN}root@osint-bot{RESET}:{CYAN}~/archive{RESET}$ paste-search {keyword}\n\n"
                        f"{RED}error{RESET}: {WHITE}no RAPIDAPI_KEY configured{RESET}"
                    ),
                    color=EMBED_COLOR,
                )
                embed.add_field(
                    name="Setup required",
                    value=(
                        "This uses BreachDirectory's paste search, hosted on RapidAPI "
                        "(free tier available). Subscribe at "
                        "https://rapidapi.com/rohan-patra/api/breachdirectory, copy your "
                        "RapidAPI key, then add `RAPIDAPI_KEY=your_key` to your `.env`.\n\n"
                        "Note: the previous provider this command used (psbdmp.ws) has "
                        "shut down permanently, which is why this was swapped."
                    ),
                    inline=False,
                )
                embed.set_footer(text=f"Requested by {ctx.author}")
                await ctx.reply(embed=embed)
                return

            url = "https://breachdirectory.p.rapidapi.com/"
            headers = {
                "X-RapidAPI-Key": api_key,
                "X-RapidAPI-Host": "breachdirectory.p.rapidapi.com",
            }
            params = {"func": "auto", "term": keyword}

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url,
                        headers=headers,
                        params=params,
                        timeout=aiohttp.ClientTimeout(total=15),
                    ) as resp:
                        if resp.status == 404:
                            await ctx.reply(f"No public pastes found containing `{keyword}`.")
                            return
                        if resp.status != 200:
                            await ctx.reply(
                                f"Paste search returned HTTP `{resp.status}` "
                                "(check your RapidAPI key/quota)."
                            )
                            return
                        payload = await resp.json()
            except Exception as e:
                await ctx.reply(f"Couldn't reach the paste search service: `{e}`")
                return

            results = payload if isinstance(payload, list) else payload.get("result", [])

            lines = f"{GREEN}root@osint-bot{RESET}:{CYAN}~/archive{RESET}$ paste-search {keyword}\n\n"

            if not results:
                lines += f"{GREEN}no public pastes found containing this keyword{RESET}"
            else:
                for entry in results[:10]:
                    paste_id = entry.get("id", "unknown")
                    date = entry.get("date", entry.get("time", "N/A"))
                    lines += f"{YELLOW}[{paste_id}]{RESET}  {WHITE}{date}{RESET}\n"
                    lines += f"    {GREY}└─{RESET} {CYAN}https://pastebin.com/{paste_id}{RESET}\n"

            embed = discord.Embed(
                title="🗄️  PASTE DUMP SEARCH",
                description=f"**Results for `{keyword}`**\n\n{ansi_block(lines.rstrip())}",
                color=EMBED_COLOR,
            )
            embed.add_field(
                name="⚠️ Note",
                value=(
                    "This searches an index of historically public pastes — useful for spotting "
                    "accidental data leaks (credentials, configs, internal docs). It only reflects "
                    "content that was already posted publicly, and results may be outdated or removed."
                ),
                inline=False,
            )
            embed.set_footer(
                text=f"Requested by {ctx.author} • data via breachdirectory.com",
                icon_url=ctx.author.display_avatar.url,
            )
            await ctx.reply(embed=embed)

    async def cog_command_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply(f"Usage: `.{ctx.command.name} <{error.param.name}>`")
        else:
            await ctx.reply(f"An error occurred: `{error}`")


async def setup(bot: commands.Bot):
    await bot.add_cog(Archive(bot))
