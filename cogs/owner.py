import os
import sys
import subprocess
import asyncio
import discord
from discord.ext import commands

EMBED_COLOR = discord.Color.from_rgb(57, 255, 20)

RESET = "\u001b[0m"
GREEN = "\u001b[1;32m"
CYAN = "\u001b[1;36m"
WHITE = "\u001b[1;37m"
YELLOW = "\u001b[1;33m"
RED = "\u001b[1;31m"

OWNER_ID = int(os.getenv("OWNER_ID", "0"))


def ansi_block(lines: str) -> str:
    return f"```ansi\n{lines}\n```"


def is_owner(ctx: commands.Context) -> bool:
    return ctx.author.id == OWNER_ID


class ConfirmView(discord.ui.View):
    def __init__(self, ctx: commands.Context, action: str):
        super().__init__(timeout=20)
        self.ctx = ctx
        self.action = action  
        self.message: discord.Message | None = None
        self.confirmed = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                "This prompt isn't for you.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Yes, I'm sure", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = True
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="✖️")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = False
        for item in self.children:
            item.disabled = True
        embed = discord.Embed(
            description=ansi_block(
                f"{GREEN}root@osint-bot{RESET}:{CYAN}~{RESET}$ {self.action}\n"
                f"{YELLOW}aborted by operator{RESET}"
            ),
            color=EMBED_COLOR,
        )
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    async def on_timeout(self):
        self.confirmed = False
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                embed = discord.Embed(
                    description=ansi_block(
                        f"{GREEN}root@osint-bot{RESET}:{CYAN}~{RESET}$ {self.action}\n"
                        f"{YELLOW}timed out, no response — aborted{RESET}"
                    ),
                    color=EMBED_COLOR,
                )
                await self.message.edit(embed=embed, view=self)
            except discord.HTTPException:
                pass


async def run_stages(message: discord.Message, action: str, stages: list[str]):
    log = f"{GREEN}root@osint-bot{RESET}:{CYAN}~{RESET}$ {action}\n\n"
    for i, stage in enumerate(stages):
        log += f"{WHITE}[{i + 1}/{len(stages)}]{RESET} {stage}{GREEN} ✓{RESET}\n"
        embed = discord.Embed(description=ansi_block(log.rstrip()), color=EMBED_COLOR)
        await message.edit(embed=embed, view=None)
        await asyncio.sleep(0.8)


class Owner(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _deny(self, ctx: commands.Context):
        lines = (
            f"{GREEN}root@osint-bot{RESET}:{CYAN}~{RESET}$ {ctx.prefix}{ctx.invoked_with}\n"
            f"{RED}permission denied: you are not the bot owner{RESET}"
        )
        embed = discord.Embed(
            title="⛔  ACCESS DENIED",
            description=ansi_block(lines),
            color=discord.Color.red(),
        )
        embed.set_footer(text=f"Attempted by {ctx.author}")
        await ctx.reply(embed=embed)

    
    @commands.command()
    async def shutdown(self, ctx: commands.Context):
        if not is_owner(ctx):
            await self._deny(ctx)
            return

        embed = discord.Embed(
            title="⚠️  CONFIRM SHUTDOWN",
            description=ansi_block(
                f"{GREEN}root@osint-bot{RESET}:{CYAN}~{RESET}$ shutdown\n"
                f"{YELLOW}are you sure you want to shut down the bot?{RESET}"
            ),
            color=EMBED_COLOR,
        )
        embed.set_footer(text=f"Requested by {ctx.author}")
        view = ConfirmView(ctx, "shutdown")
        message = await ctx.reply(embed=embed, view=view)
        view.message = message

        await view.wait()
        if not view.confirmed:
            return

        stages = [
            "saving state...",
            "closing active sessions...",
            "disconnecting from discord gateway...",
        ]
        await run_stages(message, "shutdown", stages)

        final = discord.Embed(
            description=ansi_block(
                f"{GREEN}root@osint-bot{RESET}:{CYAN}~{RESET}$ shutdown\n\n"
                f"{RED}system halted.{RESET} {WHITE}goodbye 👋{RESET}"
            ),
            color=EMBED_COLOR,
        )
        await message.edit(embed=final)
        await self.bot.close()

    
    @commands.command()
    async def restart(self, ctx: commands.Context):
        if not is_owner(ctx):
            await self._deny(ctx)
            return

        embed = discord.Embed(
            title="⚠️  CONFIRM RESTART",
            description=ansi_block(
                f"{GREEN}root@osint-bot{RESET}:{CYAN}~{RESET}$ restart\n"
                f"{YELLOW}are you sure you want to restart the bot?{RESET}"
            ),
            color=EMBED_COLOR,
        )
        embed.set_footer(text=f"Requested by {ctx.author}")
        view = ConfirmView(ctx, "restart")
        message = await ctx.reply(embed=embed, view=view)
        view.message = message

        await view.wait()
        if not view.confirmed:
            return

        stages = [
            "saving state...",
            "closing active sessions...",
            "reloading process...",
        ]
        await run_stages(message, "restart", stages)

        final = discord.Embed(
            description=ansi_block(
                f"{GREEN}root@osint-bot{RESET}:{CYAN}~{RESET}$ restart\n\n"
                f"{GREEN}restarting now...{RESET}"
            ),
            color=EMBED_COLOR,
        )
        await message.edit(embed=final)
        await self.bot.close()

        
        if sys.platform == "win32":
            subprocess.Popen([sys.executable] + sys.argv, creationflags=subprocess.DETACHED_PROCESS)
        else:
            
            
            subprocess.Popen([sys.executable] + sys.argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        os._exit(0)

async def setup(bot: commands.Bot):
    await bot.add_cog(Owner(bot))
