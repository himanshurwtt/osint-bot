
import os
import time
import asyncio
import platform
import discord
from discord.ext import commands
from datetime import datetime, timezone

try:
    import psutil
except ImportError:
    psutil = None


EMBED_COLOR = discord.Color.from_rgb(57, 255, 20)

RESET = "\u001b[0m"
GREEN = "\u001b[1;32m"
CYAN = "\u001b[1;36m"
YELLOW = "\u001b[1;33m"
BLUE = "\u001b[1;34m"
GREY = "\u001b[0;30m"
WHITE = "\u001b[1;37m"
RED = "\u001b[1;31m"

OWNER_ID = int(os.getenv("OWNER_ID", "0"))


def ansi_block(lines: str) -> str:
    return f"```ansi\n{lines}\n```"


def kv(key: str, value: str) -> str:
    return f"{CYAN}{key}{RESET}: {WHITE}{value}{RESET}"


def latency_color(ms: float) -> str:
    if ms < 150:
        return GREEN
    if ms < 300:
        return YELLOW
    return RED


CATEGORIES = {
    "general": {
        "label": "General",
        "emoji": "🌐",
        "description": "Core bot commands",
        "commands": {
            ".ping": "Check the bot's latency",
            ".help": "Show this help panel",
            ".botinfo": "Show bot stats, system info, and developer credits",
        },
    },
    "username": {
        "label": "Username Recon",
        "emoji": "🔎",
        "description": "Look up usernames across platforms",
        "commands": {
            ".username <name>": "Search for a username across common platforms",
            ".namecheck <name>": "Check a name/handle across all supported platforms",
        },
    },
    "domain": {
        "label": "Domain & IP",
        "emoji": "🖥️",
        "description": "WHOIS, DNS, and IP intel lookups",
        "commands": {
            ".whois <domain>": "Get WHOIS registration info for a domain",
            ".dns <domain>": "Fetch DNS records for a domain",
            ".ipinfo <ip>": "Get geolocation and ISP info for an IP",
            ".certs <domain>": "Pull Certificate Transparency logs (crt.sh)",
            ".techstack <url>": "Fingerprint a site's tech stack (CMS, JS, CDN)",
            ".subdomains <domain>": "Discover subdomains via CT logs + brute force",
            ".robots <domain>": "Fetch and parse robots.txt / sitemap.xml",
            ".typosquat <domain>": "Check common typo variants of a domain",
            ".netping <host>": "Real ICMP ping to a website or IP address",
        },
    },
    "email": {
        "label": "Email Recon",
        "emoji": "📧",
        "description": "Email validation and exposure checks",
        "commands": {
            ".emailcheck <email>": "Validate email format and mail server",
            ".breach <email>": "Check public breach databases for an email",
        },
    },
    "social": {
        "label": "Social Media",
        "emoji": "📱",
        "description": "Public social media profile lookups",
        "commands": {
            ".social <name>": "Search public social profiles by name/handle",
        },
    },
    "image": {
        "label": "Image Recon",
        "emoji": "🖼️",
        "description": "Reverse image search tools",
        "commands": {
            ".reverse <image_url>": "Get reverse image search links",
            ".exif <image_url>": "Extract EXIF metadata from an image",
        },
    },
    "threat": {
        "label": "Threat Intel",
        "emoji": "🛡️",
        "description": "IP reputation, malware hash, and favicon pivoting",
        "commands": {
            ".iprep <ip>": "Check an IP's abuse/reputation history",
            ".hashcheck <hash>": "Check a file hash against VirusTotal",
            ".favhash <url>": "Hash a site's favicon and pivot via Shodan",
        },
    },
    "archive": {
        "label": "Archive & Leaks",
        "emoji": "🗄️",
        "description": "Historical snapshots and leaked-paste search",
        "commands": {
            ".wayback <url>": "Check Wayback Machine snapshot history",
            ".pastesearch <keyword>": "Search public paste dumps for a keyword",
        },
    },
    "crypto": {
        "label": "Crypto Recon",
        "emoji": "💰",
        "description": "Public blockchain wallet lookups",
        "commands": {
            ".wallet <address>": "Get balance/tx info for a BTC or ETH address",
        },
    },
    "owner": {
        "label": "Owner",
        "emoji": "🛡️",
        "description": "Bot control — restricted to the owner",
        "commands": {
            ".shutdown": "Safely shut down the bot",
            ".restart": "Restart the bot process",
        },
    },
}


def terminal_block(lines: str) -> str:
    return f"```ansi\n{lines}\n```"


def visible_categories(ctx: commands.Context) -> dict:
    if ctx.author.id == OWNER_ID:
        return CATEGORIES
    return {k: v for k, v in CATEGORIES.items() if k != "owner"}


def build_home_embed(bot: commands.Bot, ctx: commands.Context) -> discord.Embed:
    now = datetime.now(timezone.utc).strftime("%A, %Y-%m-%d %H:%M UTC")
    categories = visible_categories(ctx)

    lines = f"{GREEN}root@osint-bot{RESET}:{BLUE}~{RESET}$ ls categories/\n\n"
    for cat in categories.values():
        lines += (
            f"{YELLOW}[{cat['label']}]{RESET}  "
            f"{WHITE}{cat['description']}{RESET}  "
            f"{CYAN}({len(cat['commands'])} cmds){RESET}\n"
        )

    embed = discord.Embed(
        title="🖥️  OSINT-BOT // HELP TERMINAL",
        description=(
            f"{terminal_block(lines)}\n"
            f"> Authenticated as **{ctx.author}**\n"
            f"> Prefix: `{bot.command_prefix}` • Categories: `{len(categories)}` • {now}\n\n"
            "Select a category from the dropdown below to view its commands."
        ),
        color=EMBED_COLOR,
    )
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    embed.set_footer(
        text=f"session opened by {ctx.author}",
        icon_url=ctx.author.display_avatar.url,
    )
    return embed


def build_category_embed(key: str) -> discord.Embed:
    cat = CATEGORIES[key]

    lines = f"{GREEN}root@osint-bot{RESET}:{BLUE}~/{key}{RESET}$ list\n\n"
    for cmd, desc in cat["commands"].items():
        lines += f"{CYAN}{cmd}{RESET}\n    {GREY}└─{RESET} {WHITE}{desc}{RESET}\n"

    embed = discord.Embed(
        title=f"{cat['emoji']}  {cat['label'].upper()} // MODULE",
        description=(
            f"{terminal_block(lines)}\n"
            f"> {cat['description']}"
        ),
        color=EMBED_COLOR,
    )
    embed.set_footer(text="Use the dropdown to jump to another module")
    return embed


class HelpDropdown(discord.ui.Select):
    def __init__(self, bot: commands.Bot, ctx: commands.Context):
        self.bot = bot
        self.ctx = ctx
        options = [
            discord.SelectOption(
                label="Home",
                emoji="🏠",
                description="Back to the main terminal",
                value="home",
            )
        ]
        for key, cat in visible_categories(ctx).items():
            options.append(
                discord.SelectOption(
                    label=cat["label"],
                    emoji=cat["emoji"],
                    description=cat["description"],
                    value=key,
                )
            )
        super().__init__(
            placeholder="root@osint-bot:~$ select module...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                "Access denied — this session belongs to someone else. Run `.help` yourself.",
                ephemeral=True,
            )
            return

        selected = self.values[0]
        if selected == "owner" and interaction.user.id != OWNER_ID:
            await interaction.response.send_message(
                "Access denied — that module is restricted to the bot owner.",
                ephemeral=True,
            )
            return

        if selected == "home":
            embed = build_home_embed(self.bot, self.ctx)
        else:
            embed = build_category_embed(selected)

        await interaction.response.edit_message(embed=embed)


class HelpView(discord.ui.View):
    def __init__(self, bot: commands.Bot, ctx: commands.Context):
        super().__init__(timeout=60)
        self.bot = bot
        self.ctx = ctx
        self.message: discord.Message | None = None
        self.add_item(HelpDropdown(bot, ctx))

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


BOT_VERSION = 'v2.0.0 — "Full Spectrum"'

CHANGELOG = [
    "Added Threat Intel module: .iprep, .hashcheck, .favhash",
    "Added Archive & Leaks module: .wayback, .pastesearch",
    "Added Crypto Recon module: .wallet",
    "Added Domain expansion: .certs, .techstack, .subdomains, .robots, .typosquat",
    "Added Image Recon: .reverse, .exif",
    "Added Social Recon: .social (10 platforms + shared-server Discord lookup)",
    "Added real ICMP .netping alongside the simulated .ping",
    "Unified .namecheck and .username into a single full 12-platform scan",
    "Fixed critical .restart crash and silent global error handling",
]

DEVELOPER_NAME = "Himanshu Rawat"
DEVELOPER_DISCORD = "geek7"
DEVELOPER_GITHUB = "himanshurwtt"
DEVELOPER_INSTAGRAM = "himanshuurwt"


def format_uptime(delta_seconds: float) -> str:
    days, rem = divmod(int(delta_seconds), 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts)


class General(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    
    @commands.command()
    async def ping(self, ctx: commands.Context):
        target = self.bot.user.name.lower()
        packet_count = 5

        placeholder_embed = discord.Embed(
            description=ansi_block(
                f"{GREEN}root@osint-bot{RESET}:{CYAN}~{RESET}$ ping {target}\n\n{WHITE}pinging...{RESET}"
            ),
            color=EMBED_COLOR,
        )
        message = await ctx.reply(embed=placeholder_embed)

        samples = []
        for _ in range(packet_count):
            start = time.perf_counter()
            await message.edit(embed=placeholder_embed)
            elapsed_ms = round((time.perf_counter() - start) * 1000)
            samples.append(elapsed_ms)
            await asyncio.sleep(0.3)

        transmitted = len(samples)
        received = len(samples)
        avg_latency = round(sum(samples) / len(samples))
        ws_latency = round(self.bot.latency * 1000)

        lines = f"{GREEN}root@osint-bot{RESET}:{CYAN}~{RESET}$ ping {target}\n\n"
        for i, ms in enumerate(samples, start=1):
            color = latency_color(ms)
            lines += f"{WHITE}from {target}, seq={i}{RESET}  {color}{ms} ms{RESET}\n"

        lines += (
            f"\n{YELLOW}--- {target} ping statistics ---{RESET}\n"
            f"{WHITE}{transmitted} packets transmitted, {received} packets received, "
            f"0% packet loss{RESET}\n"
            f"{WHITE}avg latency: {latency_color(avg_latency)}{avg_latency} ms{RESET}\n"
            f"{WHITE}websocket: {latency_color(ws_latency)}{ws_latency} ms{RESET}\n"
            f"{WHITE}status code: {GREEN}200{RESET}"
        )

        embed = discord.Embed(
            title="🏓  PONG",
            description=ansi_block(lines),
            color=EMBED_COLOR,
        )
        embed.set_footer(
            text=f"Requested by {ctx.author}",
            icon_url=ctx.author.display_avatar.url,
        )
        await message.edit(embed=embed)

    
    @commands.command()
    async def help(self, ctx: commands.Context):
        view = HelpView(self.bot, ctx)
        embed = build_home_embed(self.bot, ctx)
        message = await ctx.reply(embed=embed, view=view)
        view.message = message

    
    @commands.command()
    async def botinfo(self, ctx: commands.Context):
        async with ctx.typing():
            bot = self.bot

            launch_time = getattr(bot, "launch_time", None)
            uptime_str = "unknown"
            if launch_time:
                uptime_str = format_uptime((datetime.now(timezone.utc) - launch_time).total_seconds())

            latency_ms = round(bot.latency * 1000)
            guild_count = len(bot.guilds)
            user_count = sum(g.member_count or 0 for g in bot.guilds)
            command_count = len(bot.commands)
            cog_count = len(bot.cogs)

            lines = f"{GREEN}root@osint-bot{RESET}:{CYAN}~{RESET}$ botinfo\n\n"
            lines += kv("bot", str(bot.user)) + "\n"
            lines += kv("version", BOT_VERSION) + "\n"
            lines += kv("uptime", uptime_str) + "\n"
            lines += kv("latency", f"{latency_ms}ms") + "\n"
            lines += kv("servers", str(guild_count)) + "\n"
            lines += kv("users_visible", str(user_count)) + "\n"
            lines += kv("commands_loaded", str(command_count)) + "\n"
            lines += kv("modules_loaded", str(cog_count)) + "\n"
            lines += kv("python", platform.python_version()) + "\n"
            lines += kv("discord.py", discord.__version__)

            embed = discord.Embed(
                title="🖥️  BOT INFO // SYSTEM CARD",
                description=ansi_block(lines),
                color=EMBED_COLOR,
            )
            embed.set_thumbnail(url=bot.user.display_avatar.url)

            if psutil:
                process = psutil.Process()
                cpu_percent = psutil.cpu_percent(interval=0.3)
                mem_info = process.memory_info()
                mem_mb = mem_info.rss / (1024 * 1024)
                total_mem = psutil.virtual_memory().total / (1024 * 1024)

                sys_lines = f"{GREEN}root@osint-bot{RESET}:{CYAN}~{RESET}$ htop\n\n"
                sys_lines += kv("cpu_usage", f"{cpu_percent:.1f}%") + "\n"
                sys_lines += kv("ram_usage", f"{mem_mb:.1f} MB / {total_mem:.0f} MB") + "\n"
                sys_lines += kv("os", f"{platform.system()} {platform.release()}") + "\n"
                sys_lines += kv("architecture", platform.machine())

                embed.add_field(name="⚙️ System", value=ansi_block(sys_lines), inline=False)
            else:
                embed.add_field(
                    name="⚙️ System",
                    value="Install `psutil` (`pip install psutil`) to show live CPU/RAM usage here.",
                    inline=False,
                )

            changelog_lines = "\n".join(f"{GREEN}•{RESET} {WHITE}{item}{RESET}" for item in CHANGELOG[:8])
            embed.add_field(name="📜 Recent changes", value=ansi_block(changelog_lines), inline=False)

            dev_lines = (
                f"{kv('name', DEVELOPER_NAME)}\n"
                f"{kv('discord', DEVELOPER_DISCORD)}\n"
                f"{kv('github', DEVELOPER_GITHUB)}\n"
                f"{kv('instagram', DEVELOPER_INSTAGRAM)}"
            )
            embed.add_field(name="👤 Developer", value=ansi_block(dev_lines), inline=False)

            embed.set_footer(
                text=f"Requested by {ctx.author} • built with discord.py",
                icon_url=ctx.author.display_avatar.url,
            )
            await ctx.reply(embed=embed)

    async def cog_command_error(self, ctx: commands.Context, error):
        await ctx.reply(f"An error occurred: `{error}`")


async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))
