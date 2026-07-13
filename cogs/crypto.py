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


def detect_chain(address: str) -> str:
    if address.startswith(("1", "3", "bc1")):
        return "btc"
    if address.startswith("0x") and len(address) == 42:
        return "eth"
    return "unknown"


class Crypto(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    
    @commands.command()
    async def wallet(self, ctx: commands.Context, address: str):
        async with ctx.typing():
            chain = detect_chain(address)

            if chain == "unknown":
                await ctx.reply(
                    "Couldn't recognize that address format. Supported: "
                    "Bitcoin (`1...`, `3...`, `bc1...`) or Ethereum (`0x...`)."
                )
                return

            url = f"https://api.blockcypher.com/v1/{chain}/main/addrs/{address}/balance"

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url,
                        headers={"User-Agent": USER_AGENT},
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as resp:
                        if resp.status == 404:
                            await ctx.reply(f"No on-chain activity found for `{address}`.")
                            return
                        if resp.status != 200:
                            await ctx.reply(f"BlockCypher returned HTTP `{resp.status}` (rate limits are strict on the free tier).")
                            return
                        data = await resp.json()
            except Exception as e:
                await ctx.reply(f"Couldn't reach the blockchain API: `{e}`")
                return

            if chain == "btc":
                balance = data.get("final_balance", 0) / 1e8
                unit = "BTC"
            else:
                balance = data.get("final_balance", 0) / 1e18
                unit = "ETH"

            total_received = data.get("total_received", 0)
            total_sent = data.get("total_sent", 0)
            divisor = 1e8 if chain == "btc" else 1e18
            n_tx = data.get("final_n_tx", data.get("n_tx", 0))

            explorer_url = (
                f"https://www.blockchain.com/btc/address/{address}"
                if chain == "btc"
                else f"https://etherscan.io/address/{address}"
            )

            lines = f"{GREEN}root@osint-bot{RESET}:{CYAN}~/crypto{RESET}$ wallet-lookup {address}\n\n"
            lines += kv("chain", chain.upper()) + "\n"
            lines += kv("balance", f"{balance:.8f} {unit}") + "\n"
            lines += kv("total_received", f"{total_received / divisor:.8f} {unit}") + "\n"
            lines += kv("total_sent", f"{total_sent / divisor:.8f} {unit}") + "\n"
            lines += kv("tx_count", str(n_tx)) + "\n"
            lines += kv("explorer", explorer_url)

            embed = discord.Embed(
                title="💰  WALLET LOOKUP",
                description=f"**Report for `{address}`**\n\n{ansi_block(lines)}",
                color=EMBED_COLOR,
            )
            embed.add_field(
                name="⚠️ Note",
                value="All blockchain data is public by design — this shows nothing that isn't already visible to anyone via a block explorer. It does not reveal who owns the wallet.",
                inline=False,
            )
            embed.set_footer(
                text=f"Requested by {ctx.author} • data via blockcypher.com",
                icon_url=ctx.author.display_avatar.url,
            )
            await ctx.reply(embed=embed)

    async def cog_command_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply(f"Usage: `.{ctx.command.name} <address>`")
        else:
            await ctx.reply(f"An error occurred: `{error}`")


async def setup(bot: commands.Bot):
    await bot.add_cog(Crypto(bot))
