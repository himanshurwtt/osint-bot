import os
import base64
import hashlib
import discord
from discord.ext import commands
import aiohttp

try:
    import mmh3
except ImportError:
    mmh3 = None

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


class Threat(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    
    @commands.command()
    async def iprep(self, ctx: commands.Context, ip: str):
        async with ctx.typing():
            api_key = os.getenv("ABUSEIPDB_API_KEY")

            if not api_key:
                embed = discord.Embed(
                    title="🛡️  IP REPUTATION",
                    description=ansi_block(
                        f"{GREEN}root@osint-bot{RESET}:{CYAN}~/threat{RESET}$ iprep {ip}\n\n"
                        f"{RED}error{RESET}: {WHITE}no ABUSEIPDB_API_KEY configured{RESET}"
                    ),
                    color=EMBED_COLOR,
                )
                embed.add_field(
                    name="Setup required",
                    value=(
                        "Get a free API key at https://www.abuseipdb.com/api "
                        "(1,000 checks/day on the free tier), then add "
                        "`ABUSEIPDB_API_KEY=your_key` to your `.env`."
                    ),
                    inline=False,
                )
                embed.set_footer(text=f"Requested by {ctx.author}")
                await ctx.reply(embed=embed)
                return

            url = "https://api.abuseipdb.com/api/v2/check"
            headers = {"Key": api_key, "Accept": "application/json"}
            params = {"ipAddress": ip, "maxAgeInDays": "90", "verbose": ""}

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url, headers=headers, params=params,
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as resp:
                        if resp.status != 200:
                            await ctx.reply(f"AbuseIPDB returned HTTP `{resp.status}`.")
                            return
                        payload = await resp.json()
            except Exception as e:
                await ctx.reply(f"Couldn't reach AbuseIPDB: `{e}`")
                return

            data = payload.get("data", {})
            score = data.get("abuseConfidenceScore", 0)
            score_color = GREEN if score < 25 else (YELLOW if score < 75 else RED)

            lines = f"{GREEN}root@osint-bot{RESET}:{CYAN}~/threat{RESET}$ iprep {ip}\n\n"
            lines += kv("abuse_confidence", f"{score_color}{score}%{RESET}") + "\n"
            lines += kv("country", data.get("countryCode", "N/A")) + "\n"
            lines += kv("isp", data.get("isp", "N/A")) + "\n"
            lines += kv("domain", data.get("domain", "N/A")) + "\n"
            lines += kv("usage_type", data.get("usageType", "N/A")) + "\n"
            lines += kv("total_reports", str(data.get("totalReports", 0))) + "\n"
            lines += kv("is_tor", str(data.get("isTor", False))) + "\n"
            lines += kv("last_reported", str(data.get("lastReportedAt", "never")))

            embed = discord.Embed(
                title="🛡️  IP REPUTATION",
                description=f"**Report for ({ip})**\n\n{ansi_block(lines)}",
                color=EMBED_COLOR,
            )
            embed.set_footer(
                text=f"Requested by {ctx.author} • data via abuseipdb.com",
                icon_url=ctx.author.display_avatar.url,
            )
            await ctx.reply(embed=embed)

    
    @commands.command()
    async def hashcheck(self, ctx: commands.Context, file_hash: str):
        async with ctx.typing():
            api_key = os.getenv("VIRUSTOTAL_API_KEY")

            if not api_key:
                embed = discord.Embed(
                    title="🛡️  HASH CHECK",
                    description=ansi_block(
                        f"{GREEN}root@osint-bot{RESET}:{CYAN}~/threat{RESET}$ hashcheck {file_hash}\n\n"
                        f"{RED}error{RESET}: {WHITE}no VIRUSTOTAL_API_KEY configured{RESET}"
                    ),
                    color=EMBED_COLOR,
                )
                embed.add_field(
                    name="Setup required",
                    value=(
                        "Get a free API key at https://www.virustotal.com/gui/join-us "
                        "(free tier: 500 lookups/day), then add "
                        "`VIRUSTOTAL_API_KEY=your_key` to your `.env`."
                    ),
                    inline=False,
                )
                embed.set_footer(text=f"Requested by {ctx.author}")
                await ctx.reply(embed=embed)
                return

            url = f"https://www.virustotal.com/api/v3/files/{file_hash}"
            headers = {"x-apikey": api_key}

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url, headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as resp:
                        if resp.status == 404:
                            await ctx.reply(f"No VirusTotal record found for `{file_hash}`.")
                            return
                        if resp.status != 200:
                            await ctx.reply(f"VirusTotal returned HTTP `{resp.status}`.")
                            return
                        payload = await resp.json()
            except Exception as e:
                await ctx.reply(f"Couldn't reach VirusTotal: `{e}`")
                return

            attrs = payload.get("data", {}).get("attributes", {})
            stats = attrs.get("last_analysis_stats", {})
            malicious = stats.get("malicious", 0)
            suspicious = stats.get("suspicious", 0)
            harmless = stats.get("harmless", 0)
            undetected = stats.get("undetected", 0)
            total = malicious + suspicious + harmless + undetected

            verdict_color = RED if malicious > 0 else (YELLOW if suspicious > 0 else GREEN)

            lines = f"{GREEN}root@osint-bot{RESET}:{CYAN}~/threat{RESET}$ hashcheck {file_hash}\n\n"
            lines += kv("detections", f"{verdict_color}{malicious}/{total}{RESET} engines flagged malicious") + "\n"
            lines += kv("suspicious", str(suspicious)) + "\n"
            lines += kv("file_type", attrs.get("type_description", "N/A")) + "\n"
            lines += kv("file_size", f"{attrs.get('size', 0) / 1024:.1f} KB") + "\n"
            names = attrs.get("names", [])
            if names:
                lines += kv("known_names", ", ".join(names[:3])) + "\n"
            lines += kv("first_seen", str(attrs.get("first_submission_date", "N/A")))

            embed = discord.Embed(
                title="🛡️  FILE HASH CHECK",
                description=f"**Report for `{file_hash}`**\n\n{ansi_block(lines)}",
                color=EMBED_COLOR,
            )
            embed.set_footer(
                text=f"Requested by {ctx.author} • data via virustotal.com",
                icon_url=ctx.author.display_avatar.url,
            )
            await ctx.reply(embed=embed)

    
    @commands.command()
    async def favhash(self, ctx: commands.Context, url: str):
        async with ctx.typing():
            if mmh3 is None:
                await ctx.reply(
                    "This command needs the `mmh3` package. Install it with "
                    "`pip install mmh3` and restart the bot."
                )
                return

            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            favicon_url = url.rstrip("/") + "/favicon.ico"

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        favicon_url,
                        headers={"User-Agent": USER_AGENT},
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as resp:
                        if resp.status != 200:
                            await ctx.reply(f"No favicon found at `{favicon_url}` (HTTP `{resp.status}`).")
                            return
                        raw = await resp.read()
            except Exception as e:
                await ctx.reply(f"Couldn't fetch favicon: `{e}`")
                return

            b64 = base64.encodebytes(raw)
            favicon_hash = mmh3.hash(b64)

            lines = f"{GREEN}root@osint-bot{RESET}:{CYAN}~/threat{RESET}$ favicon-hash {url}\n\n"
            lines += kv("favicon_url", favicon_url) + "\n"
            lines += kv("mmh3_hash", str(favicon_hash)) + "\n"
            lines += kv("md5", hashlib.md5(raw).hexdigest())

            embed = discord.Embed(
                title="🎯  FAVICON HASH",
                description=f"**Hash for ({url})**\n\n{ansi_block(lines)}",
                color=EMBED_COLOR,
            )

            shodan_key = os.getenv("SHODAN_API_KEY")
            shodan_search_url = f"https://www.shodan.io/search?query=http.favicon.hash%3A{favicon_hash}"

            if shodan_key:
                count_url = f"https://api.shodan.io/shodan/host/count?key={shodan_key}&query=http.favicon.hash:{favicon_hash}"
                search_url_api = f"https://api.shodan.io/shodan/host/search?key={shodan_key}&query=http.favicon.hash:{favicon_hash}"
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(count_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                            if resp.status == 200:
                                shodan_data = await resp.json()
                                count = shodan_data.get("total", 0)

                                sample_line = ""
                                try:
                                    async with session.get(
                                        search_url_api, timeout=aiohttp.ClientTimeout(total=10)
                                    ) as search_resp:
                                        if search_resp.status == 200:
                                            search_data = await search_resp.json()
                                            matches = search_data.get("matches", [])[:5]
                                            entries = []
                                            for m in matches:
                                                ip = m.get("ip_str", "?")
                                                port = m.get("port", "?")
                                                org = (m.get("org") or "unknown")[:20]
                                                entries.append(f"{ip}:{port} ({org})")
                                            if entries:
                                                sample_line = "[ " + ", ".join(entries) + " ]"
                                except Exception:
                                    pass  

                                value = f"**{count}** other hosts share this favicon hash.\n"
                                if sample_line:
                                    value += f"```{sample_line}```"
                                value += f"[View on Shodan]({shodan_search_url})"

                                embed.add_field(
                                    name="🔎 Shodan pivot",
                                    value=value,
                                    inline=False,
                                )
                            else:
                                error_body = await resp.text()
                                embed.add_field(
                                    name="🔎 Shodan pivot",
                                    value=(
                                        f"Shodan returned HTTP `{resp.status}` "
                                        f"({error_body[:150]}). Check your API key/query credits.\n"
                                        f"[View on Shodan]({shodan_search_url})"
                                    ),
                                    inline=False,
                                )
                except Exception as e:
                    embed.add_field(
                        name="🔎 Shodan pivot",
                        value=(
                            f"Couldn't reach Shodan: `{e}`\n"
                            f"[View on Shodan]({shodan_search_url})"
                        ),
                        inline=False,
                    )
            else:
                embed.add_field(
                    name="🔎 Shodan pivot",
                    value=(
                        f"Add `SHODAN_API_KEY` to your `.env` to get a live host count. "
                        f"In the meantime, search manually: [View on Shodan]({shodan_search_url})"
                    ),
                    inline=False,
                )

            embed.add_field(
                name="⚠️ Note",
                value="Favicon hash matching finds infrastructure serving the same icon — useful for finding related sites, phishing clones, or hidden origin servers behind a CDN. Pulling sample hosts uses 1 additional Shodan query credit beyond the free count check.",
                inline=False,
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
    await bot.add_cog(Threat(bot))
