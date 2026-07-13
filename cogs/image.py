import io
import urllib.parse
import discord
from discord.ext import commands
import aiohttp
from PIL import Image as PILImage, ExifTags
from PIL.ExifTags import GPSTAGS

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

MAX_IMAGE_BYTES = 15 * 1024 * 1024  


def ansi_block(lines: str) -> str:
    return f"```ansi\n{lines}\n```"


def kv(key: str, value: str) -> str:
    return f"{CYAN}{key}{RESET}: {WHITE}{value}{RESET}"


def _dms_to_decimal(dms, ref) -> float:
    degrees, minutes, seconds = dms
    decimal = float(degrees) + float(minutes) / 60 + float(seconds) / 3600
    if ref in ("S", "W"):
        decimal = -decimal
    return decimal


def extract_gps(exif_data: dict):
    gps_raw = exif_data.get("GPSInfo")
    if not gps_raw:
        return None

    gps = {GPSTAGS.get(tag, tag): value for tag, value in gps_raw.items()}

    lat = gps.get("GPSLatitude")
    lat_ref = gps.get("GPSLatitudeRef")
    lon = gps.get("GPSLongitude")
    lon_ref = gps.get("GPSLongitudeRef")

    if not (lat and lat_ref and lon and lon_ref):
        return None

    try:
        latitude = _dms_to_decimal(lat, lat_ref)
        longitude = _dms_to_decimal(lon, lon_ref)
        return latitude, longitude
    except Exception:
        return None


class Image(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    
    @commands.command()
    async def reverse(self, ctx: commands.Context, image_url: str):
        encoded = urllib.parse.quote(image_url, safe="")

        engines = {
            "Google Lens": f"https://lens.google.com/uploadbyurl?url={encoded}",
            "Yandex": f"https://yandex.com/images/search?url={encoded}&rpt=imageview",
            "TinEye": f"https://tineye.com/search?url={encoded}",
            "Bing Visual Search": f"https://www.bing.com/images/search?q=imgurl:{encoded}&view=detailv2&iss=sbi",
        }

        lines = f"{GREEN}root@osint-bot{RESET}:{CYAN}~/image{RESET}$ reverse-search {image_url}\n\n"
        for name, url in engines.items():
            lines += f"{YELLOW}[{name}]{RESET}\n  {CYAN}{url}{RESET}\n"

        embed = discord.Embed(
            title="🖼️  REVERSE IMAGE SEARCH",
            description=ansi_block(lines.rstrip()),
            color=EMBED_COLOR,
        )
        embed.set_thumbnail(url=image_url)
        embed.add_field(
            name="⚠️ Note",
            value="These links open each engine's search directly — no data is sent through this bot.",
            inline=False,
        )
        embed.set_footer(
            text=f"Requested by {ctx.author}",
            icon_url=ctx.author.display_avatar.url,
        )
        await ctx.reply(embed=embed)

    
    @commands.command()
    async def exif(self, ctx: commands.Context, image_url: str):
        async with ctx.typing():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        image_url,
                        headers={"User-Agent": USER_AGENT},
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as resp:
                        if resp.status != 200:
                            await ctx.reply(f"Couldn't fetch image: HTTP `{resp.status}`")
                            return
                        content_length = resp.content_length
                        if content_length and content_length > MAX_IMAGE_BYTES:
                            await ctx.reply("Image is too large to process (>15 MB).")
                            return
                        raw = await resp.read()
                        if len(raw) > MAX_IMAGE_BYTES:
                            await ctx.reply("Image is too large to process (>15 MB).")
                            return
            except Exception as e:
                await ctx.reply(f"Couldn't fetch image: `{e}`")
                return

            try:
                img = PILImage.open(io.BytesIO(raw))
                img.load()
            except Exception as e:
                await ctx.reply(f"Couldn't read image data: `{e}`")
                return

            width, height = img.size
            fmt = img.format or "unknown"
            mode = img.mode

            raw_exif = img.getexif()
            exif_data = {}
            if raw_exif:
                for tag_id, value in raw_exif.items():
                    tag = ExifTags.TAGS.get(tag_id, tag_id)
                    exif_data[tag] = value
                
                try:
                    gps_ifd = raw_exif.get_ifd(ExifTags.IFD.GPSInfo)
                    if gps_ifd:
                        exif_data["GPSInfo"] = gps_ifd
                except Exception:
                    pass

            lines = f"{GREEN}root@osint-bot{RESET}:{CYAN}~/image{RESET}$ exiftool {image_url}\n\n"
            lines += kv("format", fmt) + "\n"
            lines += kv("dimensions", f"{width}x{height}") + "\n"
            lines += kv("color_mode", mode) + "\n"
            lines += kv("file_size", f"{len(raw) / 1024:.1f} KB") + "\n"

            if not exif_data:
                lines += f"\n{YELLOW}no EXIF metadata found{RESET}"
            else:
                interesting = {
                    "Make": "camera_make",
                    "Model": "camera_model",
                    "DateTime": "date_taken",
                    "DateTimeOriginal": "date_original",
                    "Software": "software",
                    "Artist": "artist",
                    "ImageDescription": "description",
                    "LensModel": "lens",
                }
                found_any = False
                for exif_key, label in interesting.items():
                    if exif_key in exif_data and exif_data[exif_key]:
                        found_any = True
                        lines += kv(label, str(exif_data[exif_key])[:60]) + "\n"

                gps = extract_gps(exif_data)
                if gps:
                    lat, lon = gps
                    lines += "\n" + kv("gps_latitude", f"{lat:.6f}") + "\n"
                    lines += kv("gps_longitude", f"{lon:.6f}") + "\n"
                    lines += kv(
                        "maps_link",
                        f"https://www.google.com/maps?q={lat:.6f},{lon:.6f}",
                    )
                elif not found_any:
                    lines += f"\n{YELLOW}EXIF tags present but none of the common fields matched{RESET}"

            embed = discord.Embed(
                title="🖼️  EXIF METADATA",
                description=ansi_block(lines.rstrip()),
                color=EMBED_COLOR,
            )
            embed.set_thumbnail(url=image_url)

            gps = extract_gps(exif_data) if exif_data else None
            if gps:
                embed.add_field(
                    name="⚠️ Location data found",
                    value=(
                        "This image contains embedded GPS coordinates. If you're sharing "
                        "this image publicly, consider stripping metadata first — most "
                        "phones embed exact location by default."
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
            await ctx.reply(f"Usage: `.{ctx.command.name} <image_url>`")
        else:
            await ctx.reply(f"An error occurred: `{error}`")


async def setup(bot: commands.Bot):
    await bot.add_cog(Image(bot))
