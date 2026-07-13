import os
import re
import asyncio
import discord
from discord.ext import commands
import aiohttp
import dns.resolver

EMBED_COLOR = discord.Color.from_rgb(57, 255, 20)

RESET = "\u001b[0m"
GREEN = "\u001b[1;32m"
CYAN = "\u001b[1;36m"
WHITE = "\u001b[1;37m"
YELLOW = "\u001b[1;33m"
RED = "\u001b[1;31m"
GREY = "\u001b[0;30m"

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


DISPOSABLE_DOMAINS = {
    "mailinator.com", "10minutemail.com", "guerrillamail.com",
    "tempmail.com", "temp-mail.org", "yopmail.com", "throwawaymail.com",
    "getnada.com", "trashmail.com", "fakeinbox.com",
}


def ansi_block(lines: str) -> str:
    return f"```ansi\n{lines}\n```"


def kv(key: str, value: str) -> str:
    return f"{CYAN}{key}{RESET}: {WHITE}{value}{RESET}"


class Email(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    
    @commands.command()
    async def emailcheck(self, ctx: commands.Context, email: str):
        async with ctx.typing():
            valid_format = bool(EMAIL_REGEX.match(email))

            domain = email.split("@")[-1].lower() if "@" in email else None
            has_mx = False
            mx_records = []

            if valid_format and domain:
                try:
                    answers = await asyncio.to_thread(dns.resolver.resolve, domain, "MX")
                    mx_records = sorted(
                        [str(r.exchange).rstrip(".") for r in answers]
                    )
                    has_mx = len(mx_records) > 0
                except Exception:
                    has_mx = False

            is_disposable = domain in DISPOSABLE_DOMAINS if domain else False

            lines = f"{GREEN}root@osint-bot{RESET}:{CYAN}~/email{RESET}$ check {email}\n\n"
            lines += kv(
                "format",
                f"{GREEN}valid{RESET}" if valid_format else f"{RED}invalid{RESET}",
            ) + "\n"

            if valid_format:
                lines += kv("domain", domain) + "\n"
                lines += kv(
                    "mx_records",
                    f"{GREEN}found{RESET}" if has_mx else f"{RED}none found{RESET}",
                ) + "\n"
                if mx_records:
                    for mx in mx_records[:5]:
                        lines += f"    {GREY}└─{RESET} {WHITE}{mx}{RESET}\n"
                lines += kv(
                    "disposable",
                    f"{YELLOW}likely{RESET}" if is_disposable else f"{GREEN}no{RESET}",
                ) + "\n"
                lines += kv(
                    "deliverable_guess",
                    f"{GREEN}plausible{RESET}" if has_mx and not is_disposable else f"{RED}unlikely{RESET}",
                )
            else:
                lines = lines.rstrip("\n")

            embed = discord.Embed(
                title="📧  EMAIL CHECK",
                description=ansi_block(lines),
                color=EMBED_COLOR,
            )
            embed.add_field(
                name="⚠️ Note",
                value=(
                    "This checks format + MX records only — it confirms the domain "
                    "*can* receive mail, not that this specific mailbox exists."
                ),
                inline=False,
            )
            embed.set_footer(
                text=f"Requested by {ctx.author}",
                icon_url=ctx.author.display_avatar.url,
            )
            await ctx.reply(embed=embed)

    
    @commands.command()
    async def breach(self, ctx: commands.Context, email: str):
        async with ctx.typing():
            api_key = os.getenv("HIBP_API_KEY")

            if not api_key:
                embed = discord.Embed(
                    title="📧  BREACH CHECK",
                    description=ansi_block(
                        f"{GREEN}root@osint-bot{RESET}:{CYAN}~/email{RESET}$ breach {email}\n\n"
                        f"{RED}error{RESET}: {WHITE}no HIBP_API_KEY configured{RESET}"
                    ),
                    color=EMBED_COLOR,
                )
                embed.add_field(
                    name="Setup required",
                    value=(
                        "Automated breach checks use the Have I Been Pwned API, which "
                        "requires a paid API key (~$3.50/month) since HIBP locked down "
                        "free access. Get one at https://haveibeenpwned.com/API/Key, "
                        "then add `HIBP_API_KEY=your_key` to your `.env`.\n\n"
                        f"In the meantime you can check manually at "
                        f"https://haveibeenpwned.com/account/{email}"
                    ),
                    inline=False,
                )
                embed.set_footer(text=f"Requested by {ctx.author}")
                await ctx.reply(embed=embed)
                return

            url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}"
            headers = {
                "hibp-api-key": api_key,
                "user-agent": "osint-bot",
            }

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url,
                        headers=headers,
                        params={"truncateResponse": "false"},
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as resp:
                        if resp.status == 404:
                            breaches = []
                        elif resp.status == 200:
                            breaches = await resp.json()
                        else:
                            await ctx.reply(
                                f"HIBP returned an unexpected status: `{resp.status}`"
                            )
                            return
            except Exception as e:
                await ctx.reply(f"Couldn't reach HIBP: `{e}`")
                return

            lines = f"{GREEN}root@osint-bot{RESET}:{CYAN}~/email{RESET}$ breach {email}\n\n"

            if not breaches:
                lines += f"{GREEN}no known breaches found{RESET}"
            else:
                lines += kv("breaches_found", f"{RED}{len(breaches)}{RESET}") + "\n\n"
                for b in breaches[:10]:
                    name = b.get("Name", "Unknown")
                    date = b.get("BreachDate", "N/A")
                    lines += f"{YELLOW}[{name}]{RESET}  {WHITE}{date}{RESET}\n"
                    classes = b.get("DataClasses", [])
                    if classes:
                        lines += f"    {GREY}└─{RESET} {WHITE}{', '.join(classes[:6])}{RESET}\n"

            embed = discord.Embed(
                title="📧  BREACH CHECK",
                description=ansi_block(lines.rstrip()),
                color=EMBED_COLOR,
            )
            embed.set_footer(
                text=f"Requested by {ctx.author} • data via haveibeenpwned.com",
                icon_url=ctx.author.display_avatar.url,
            )
            await ctx.reply(embed=embed)

    async def cog_command_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply(f"Usage: `.{ctx.command.name} <{error.param.name}>`")
        else:
            await ctx.reply(f"An error occurred: `{error}`")


async def setup(bot: commands.Bot):
    await bot.add_cog(Email(bot))