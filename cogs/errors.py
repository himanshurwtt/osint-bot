import difflib
import traceback
import discord
from discord.ext import commands

EMBED_COLOR = discord.Color.from_rgb(57, 255, 20)

RESET = "\u001b[0m"
GREEN = "\u001b[1;32m"
CYAN = "\u001b[1;36m"
WHITE = "\u001b[1;37m"
YELLOW = "\u001b[1;33m"
RED = "\u001b[1;31m"


def ansi_block(lines: str) -> str:
    return f"```ansi\n{lines}\n```"


class DidYouMeanView(discord.ui.View):
    def __init__(self, ctx: commands.Context, suggestion: str, remainder: str):
        super().__init__(timeout=30)
        self.ctx = ctx
        self.suggestion = suggestion
        self.remainder = remainder
        self.message: discord.Message | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                "This prompt isn't for you.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Yes, run it", style=discord.ButtonStyle.success, emoji="▶️")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

        try:
            await interaction.message.delete()
        except discord.HTTPException:
            pass

        new_content = f"{self.ctx.prefix}{self.suggestion}{self.remainder}"
        new_message = self.ctx.message
        new_message.content = new_content

        new_ctx = await self.ctx.bot.get_context(new_message)
        await self.ctx.bot.invoke(new_ctx)
        self.stop()

    @discord.ui.button(label="No", style=discord.ButtonStyle.danger, emoji="✖️")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            item.disabled = True
        embed = discord.Embed(
            description=ansi_block(
                f"{GREEN}root@osint-bot{RESET}:{CYAN}~{RESET}$ {RED}cancelled{RESET}"
            ),
            color=EMBED_COLOR,
        )
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class Errors(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        
        
        if ctx.cog and ctx.cog.has_error_handler():
            return

        if not isinstance(error, commands.CommandNotFound):
            
            
            traceback.print_exception(type(error), error, error.__traceback__)

            embed = discord.Embed(
                title="⚠️  COMMAND ERROR",
                description=ansi_block(
                    f"{GREEN}root@osint-bot{RESET}:{CYAN}~{RESET}$ {ctx.prefix}{ctx.invoked_with}\n"
                    f"{RED}error{RESET}: {WHITE}{error}{RESET}"
                ),
                color=EMBED_COLOR,
            )
            embed.set_footer(text=f"Requested by {ctx.author}")
            try:
                await ctx.reply(embed=embed)
            except discord.HTTPException:
                pass
            return

        attempted = ctx.invoked_with or ""
        all_names = [c.name for c in self.bot.commands]
        matches = difflib.get_close_matches(attempted, all_names, n=1, cutoff=0.4)

        if not matches:
            lines = (
                f"{GREEN}root@osint-bot{RESET}:{CYAN}~{RESET}$ {ctx.prefix}{attempted}\n"
                f"{RED}bash: {attempted}: command not found{RESET}"
            )
            embed = discord.Embed(
                title="⚠️  UNKNOWN COMMAND",
                description=ansi_block(lines),
                color=EMBED_COLOR,
            )
            embed.set_footer(text=f"Requested by {ctx.author}")
            await ctx.reply(embed=embed)
            return

        suggestion = matches[0]

        content = ctx.message.content
        prefix_len = len(ctx.prefix) if ctx.prefix else 0
        remainder = content[prefix_len + len(attempted):]

        lines = (
            f"{GREEN}root@osint-bot{RESET}:{CYAN}~{RESET}$ {ctx.prefix}{attempted}\n"
            f"{RED}bash: {attempted}: command not found{RESET}\n\n"
            f"{YELLOW}did you mean:{RESET} {CYAN}{ctx.prefix}{suggestion}{RESET}{WHITE}{remainder}{RESET} {YELLOW}?{RESET}"
        )

        embed = discord.Embed(
            title="⚠️  UNKNOWN COMMAND",
            description=ansi_block(lines),
            color=EMBED_COLOR,
        )
        embed.set_footer(text=f"Requested by {ctx.author}")

        view = DidYouMeanView(ctx, suggestion, remainder)
        message = await ctx.reply(embed=embed, view=view)
        view.message = message


async def setup(bot: commands.Bot):
    await bot.add_cog(Errors(bot))