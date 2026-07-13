import os
import re
import asyncio
import itertools
import platform
import socket
import discord
from discord.ext import commands
import aiohttp
import dns.resolver
import whois


EMBED_COLOR = discord.Color.from_rgb(57, 255, 20)

RESET = "\u001b[0m"
GREEN = "\u001b[1;32m"
CYAN = "\u001b[1;36m"
YELLOW = "\u001b[1;33m"
WHITE = "\u001b[1;37m"
GREY = "\u001b[0;30m"
RED = "\u001b[1;31m"


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

COMMON_SUBDOMAINS = [
    "www", "mail", "ftp", "webmail", "smtp", "pop", "ns1", "ns2", "cpanel",
    "autodiscover", "m", "shop", "blog", "dev", "test", "staging", "api",
    "admin", "portal", "vpn", "cdn", "app", "beta", "secure", "support",
    "help", "docs", "status", "git", "gitlab", "jenkins", "dashboard",
]


ADJACENT_KEYS = {
    "a": "qs", "b": "vn", "c": "xv", "d": "sf", "e": "wr", "f": "dg",
    "g": "fh", "h": "gj", "i": "uo", "j": "hk", "k": "jl", "l": "k",
    "m": "n", "n": "bm", "o": "ip", "p": "o", "q": "wa", "r": "et",
    "s": "ad", "t": "ry", "u": "yi", "v": "cb", "w": "qe", "x": "zc",
    "y": "tu", "z": "x",
}


def ansi_block(lines: str) -> str:
    return f"```ansi\n{lines}\n```"


def kv(key: str, value: str) -> str:
    return f"{CYAN}{key}{RESET}: {WHITE}{value}{RESET}"


def generate_typo_variants(domain: str, limit: int = 15) -> list:
    if "." not in domain:
        return []
    name, _, tld = domain.partition(".")
    variants = set()

    
    for i, ch in enumerate(name):
        for sub in ADJACENT_KEYS.get(ch, ""):
            variants.add(name[:i] + sub + name[i + 1:] + "." + tld)

    
    for i in range(len(name)):
        variants.add(name[:i] + name[i + 1:] + "." + tld)

    
    for i in range(len(name) - 1):
        swapped = name[:i] + name[i + 1] + name[i] + name[i + 2:]
        variants.add(swapped + "." + tld)

    
    for i, ch in enumerate(name):
        variants.add(name[:i] + ch + ch + name[i + 1:] + "." + tld)

    variants.discard(domain)
    return list(variants)[:limit]


async def resolve_a_record(hostname: str):
    try:
        answers = await asyncio.to_thread(dns.resolver.resolve, hostname, "A")
        return answers[0].to_text()
    except Exception:
        return None


PING_COUNT = 4
PING_TIMEOUT_SECONDS = 15


def ping_latency_color(ms: float) -> str:
    if ms < 80:
        return GREEN
    if ms < 200:
        return YELLOW
    return RED


def build_ping_args(host: str) -> list:
    system = platform.system().lower()
    if system == "windows":
        return ["ping", "-n", str(PING_COUNT), "-w", "2000", host]
    return ["ping", "-c", str(PING_COUNT), "-W", "2", host]


def parse_ping_output(output: str) -> dict:
    result = {
        "sent": None,
        "received": None,
        "loss_pct": None,
        "min_ms": None,
        "avg_ms": None,
        "max_ms": None,
    }

    loss_match = re.search(r"(\d+)% (?:packet )?loss", output, re.IGNORECASE)
    if loss_match:
        result["loss_pct"] = int(loss_match.group(1))

    sent_recv = re.search(r"Sent = (\d+), Received = (\d+)", output)  
    if sent_recv:
        result["sent"] = int(sent_recv.group(1))
        result["received"] = int(sent_recv.group(2))
    else:
        sent_recv_unix = re.search(r"(\d+) packets transmitted, (\d+)(?: packets)? received", output)
        if sent_recv_unix:
            result["sent"] = int(sent_recv_unix.group(1))
            result["received"] = int(sent_recv_unix.group(2))

    
    win_stats = re.search(
        r"Minimum = (\d+)ms, Maximum = (\d+)ms, Average = (\d+)ms", output
    )
    if win_stats:
        result["min_ms"] = int(win_stats.group(1))
        result["max_ms"] = int(win_stats.group(2))
        result["avg_ms"] = int(win_stats.group(3))
    else:
        
        unix_stats = re.search(
            r"[= ]([\d.]+)/([\d.]+)/([\d.]+)(?:/[\d.]+)? ms", output
        )
        if unix_stats:
            result["min_ms"] = float(unix_stats.group(1))
            result["avg_ms"] = float(unix_stats.group(2))
            result["max_ms"] = float(unix_stats.group(3))

    return result


class Domain(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    
    @commands.command()
    async def whois(self, ctx: commands.Context, domain: str):
        async with ctx.typing():
            try:
                data = await asyncio.to_thread(whois.whois, domain)
            except Exception as e:
                await ctx.reply(f"Couldn't fetch WHOIS data: `{e}`")
                return

            if not data or not data.domain_name:
                await ctx.reply(f"No WHOIS data found for `{domain}`.")
                return

            def fmt(value):
                if isinstance(value, list):
                    value = value[0] if value else None
                return str(value) if value else "N/A"

            def fmt_list(value, limit=4):
                if not value:
                    return "N/A"
                if not isinstance(value, list):
                    value = [value]
                items = [str(v) for v in value[:limit]]
                return ", ".join(items)

            lines = (
                f"{GREEN}root@osint-bot{RESET}:{CYAN}~/domain{RESET}$ whois {domain}\n\n"
                f"{kv('domain_name', fmt(data.domain_name))}\n"
                f"{kv('registrar', fmt(data.registrar))}\n"
                f"{kv('whois_server', fmt(getattr(data, 'whois_server', None)))}\n"
                f"{kv('creation_date', fmt(data.creation_date))}\n"
                f"{kv('expiration_date', fmt(data.expiration_date))}\n"
                f"{kv('updated_date', fmt(data.updated_date))}\n"
                f"{kv('name_servers', fmt_list(data.name_servers))}\n"
                f"{kv('status', fmt_list(data.status, limit=2))}\n"
                f"{kv('org', fmt(getattr(data, 'org', None)))}\n"
                f"{kv('country', fmt(getattr(data, 'country', None)))}"
            )

            embed = discord.Embed(
                title=f"🖥️  WHOIS LOOKUP",
                description=f"**Details on ({domain})**\n\n{ansi_block(lines)}",
                color=EMBED_COLOR,
            )
            embed.set_footer(
                text=f"Requested by {ctx.author}",
                icon_url=ctx.author.display_avatar.url,
            )
            await ctx.reply(embed=embed)

    
    @commands.command()
    async def dns(self, ctx: commands.Context, domain: str):
        async with ctx.typing():
            record_types = ["A", "AAAA", "MX", "NS", "TXT"]
            results = {}

            for rtype in record_types:
                try:
                    answers = await asyncio.to_thread(dns.resolver.resolve, domain, rtype)
                    results[rtype] = [rdata.to_text() for rdata in answers]
                except (
                    dns.resolver.NoAnswer,
                    dns.resolver.NXDOMAIN,
                    dns.resolver.NoNameservers,
                    dns.exception.Timeout,
                ):
                    results[rtype] = None
                except Exception:
                    results[rtype] = None

            if all(v is None for v in results.values()):
                await ctx.reply(f"No DNS records found for `{domain}`. Domain may not exist.")
                return

            lines = f"{GREEN}root@osint-bot{RESET}:{CYAN}~/domain{RESET}$ dig {domain}\n\n"
            for rtype, records in results.items():
                if records:
                    lines += f"{YELLOW}[{rtype}]{RESET}\n"
                    for r in records[:8]:
                        lines += f"  {WHITE}{r}{RESET}\n"
                else:
                    lines += f"{YELLOW}[{rtype}]{RESET}\n  {GREY}no records{RESET}\n"

            embed = discord.Embed(
                title="🌐  DNS LOOKUP",
                description=f"**Records for ({domain})**\n\n{ansi_block(lines.rstrip())}",
                color=EMBED_COLOR,
            )
            embed.set_footer(
                text=f"Requested by {ctx.author}",
                icon_url=ctx.author.display_avatar.url,
            )
            await ctx.reply(embed=embed)

    
    @commands.command()
    async def ipinfo(self, ctx: commands.Context, ip: str):
        async with ctx.typing():
            fields = (
                "status,message,continent,continentCode,country,countryCode,"
                "region,regionName,city,district,zip,lat,lon,timezone,offset,"
                "currency,isp,org,as,asname,reverse,mobile,proxy,hosting,query"
            )
            url = f"http://ip-api.com/json/{ip}?fields={fields}"

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        data = await resp.json()
            except Exception as e:
                await ctx.reply(f"Couldn't fetch IP info: `{e}`")
                return

            if data.get("status") != "success":
                await ctx.reply(f"Lookup failed: {data.get('message', 'unknown error')}")
                return

            def g(key, default="N/A"):
                val = data.get(key)
                return str(val) if val not in (None, "") else default

            embed = discord.Embed(
                title="📡  IP LOOKUP",
                description=f"**IP: {g('query')}**",
                color=EMBED_COLOR,
            )

            geo_lines = (
                f"{kv('status', g('status'))}\n"
                f"{kv('continent', g('continent'))} ({g('continentCode')})\n"
                f"{kv('country', g('country'))} ({g('countryCode')})\n"
                f"{kv('region', g('regionName'))} ({g('region')})\n"
                f"{kv('city', g('city'))}\n"
                f"{kv('district', g('district'))}\n"
                f"{kv('zip', g('zip'))}\n"
                f"{kv('timezone', g('timezone'))}"
            )
            embed.add_field(name="🌍 Location", value=ansi_block(geo_lines), inline=False)

            net_lines = (
                f"{kv('isp', g('isp'))}\n"
                f"{kv('org', g('org'))}\n"
                f"{kv('as', g('as'))}\n"
                f"{kv('asname', g('asname'))}\n"
                f"{kv('reverse', g('reverse'))}"
            )
            embed.add_field(name="🖧 Network", value=ansi_block(net_lines), inline=False)

            meta_lines = (
                f"{kv('offset', g('offset'))}\n"
                f"{kv('currency', g('currency'))}\n"
                f"{kv('proxy', g('proxy'))}\n"
                f"{kv('hosting', g('hosting'))}\n"
                f"{kv('mobile', g('mobile'))}"
            )
            embed.add_field(name="⚙️ Meta", value=ansi_block(meta_lines), inline=False)

            coord_lines = f"{kv('latitude', g('lat'))}\n{kv('longitude', g('lon'))}"
            embed.add_field(name="📌 Coordinates", value=ansi_block(coord_lines), inline=False)

            lat = data.get("lat")
            lon = data.get("lon")
            geoapify_key = os.getenv("GEOAPIFY_API_KEY")
            if lat is not None and lon is not None and geoapify_key:
                map_url = (
                    "https://maps.geoapify.com/v1/staticmap"
                    "?style=osm-carto&width=600&height=300"
                    f"&center=lonlat:{lon},{lat}&zoom=10"
                    f"&marker=lonlat:{lon},{lat};color:%23ff0000;size:large"
                    f"&apiKey={geoapify_key}"
                )
                embed.set_image(url=map_url)

            country_code = data.get("countryCode")
            if country_code:
                embed.set_thumbnail(url=f"https://flagcdn.com/w320/{country_code.lower()}.png")

            embed.set_footer(
                text=f"Requested by {ctx.author} • data via ip-api.com",
                icon_url=ctx.author.display_avatar.url,
            )
            await ctx.reply(embed=embed)

    
    @commands.command()
    async def certs(self, ctx: commands.Context, domain: str):
        async with ctx.typing():
            url = f"https://crt.sh/?q=%25.{domain}&output=json"
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url,
                        headers={"User-Agent": USER_AGENT},
                        timeout=aiohttp.ClientTimeout(total=15),
                    ) as resp:
                        if resp.status != 200:
                            await ctx.reply(f"crt.sh returned HTTP `{resp.status}`.")
                            return
                        try:
                            data = await resp.json(content_type=None)
                        except Exception:
                            data = []
            except Exception as e:
                await ctx.reply(f"Couldn't reach crt.sh: `{e}`")
                return

            if not data:
                await ctx.reply(f"No certificate transparency records found for `{domain}`.")
                return

            names = set()
            for entry in data:
                for n in entry.get("name_value", "").split("\n"):
                    n = n.strip().lower()
                    if n and not n.startswith("*."):
                        names.add(n)

            sorted_names = sorted(names)

            lines = f"{GREEN}root@osint-bot{RESET}:{CYAN}~/domain{RESET}$ ct-search {domain}\n\n"
            for n in sorted_names[:25]:
                lines += f"{CYAN}{n}{RESET}\n"
            if len(sorted_names) > 25:
                lines += f"{GREY}... and {len(sorted_names) - 25} more{RESET}\n"

            lines += (
                f"\n{YELLOW}--- summary ---{RESET}\n"
                f"{WHITE}unique hostnames found: {GREEN}{len(sorted_names)}{RESET}\n"
                f"{WHITE}certificates scanned: {len(data)}{RESET}"
            )

            embed = discord.Embed(
                title="📜  CERTIFICATE TRANSPARENCY",
                description=f"**CT logs for ({domain})**\n\n{ansi_block(lines.rstrip())}",
                color=EMBED_COLOR,
            )
            embed.add_field(
                name="⚠️ Note",
                value="Hostnames come from public CT logs — some may be expired, unused, or internal-only names that were never actually deployed.",
                inline=False,
            )
            embed.set_footer(
                text=f"Requested by {ctx.author} • data via crt.sh",
                icon_url=ctx.author.display_avatar.url,
            )
            await ctx.reply(embed=embed)

    
    @commands.command()
    async def techstack(self, ctx: commands.Context, url: str):
        async with ctx.typing():
            if not url.startswith(("http://", "https://")):
                url = "https://" + url

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url,
                        headers={"User-Agent": USER_AGENT},
                        timeout=aiohttp.ClientTimeout(total=10),
                        allow_redirects=True,
                    ) as resp:
                        headers = resp.headers
                        html = await resp.text(errors="ignore")
                        status = resp.status
            except Exception as e:
                await ctx.reply(f"Couldn't fetch `{url}`: `{e}`")
                return

            findings = []

            server = headers.get("Server")
            if server:
                findings.append(("Server", server))
            powered_by = headers.get("X-Powered-By")
            if powered_by:
                findings.append(("X-Powered-By", powered_by))
            cdn_header = headers.get("CF-RAY") or headers.get("X-CDN") or headers.get("X-Cache")
            if headers.get("CF-RAY"):
                findings.append(("CDN", "Cloudflare"))
            elif headers.get("X-Amz-Cf-Id"):
                findings.append(("CDN", "Amazon CloudFront"))

            signatures = {
                "WordPress": ["wp-content", "wp-includes"],
                "Shopify": ["cdn.shopify.com", "Shopify.theme"],
                "Wix": ["wix.com", "wixstatic.com"],
                "Squarespace": ["squarespace.com", "static1.squarespace.com"],
                "React": ["__NEXT_DATA__", "react-dom", "data-reactroot"],
                "Next.js": ["__NEXT_DATA__", "/_next/static"],
                "Vue.js": ["__vue__", "vue.js", "data-v-"],
                "Angular": ["ng-version", "angular.js"],
                "jQuery": ["jquery.js", "jquery.min.js"],
                "Bootstrap": ["bootstrap.min.css", "bootstrap.min.js"],
                "Google Analytics": ["www.google-analytics.com", "gtag("],
                "Google Tag Manager": ["googletagmanager.com"],
                "Cloudflare": ["cloudflare.com", "cf-ray"],
            }

            html_lower = html.lower()
            for tech, markers in signatures.items():
                if any(marker.lower() in html_lower for marker in markers):
                    findings.append(("Detected", tech))

            generator_match = re.search(
                r'<meta[^>]+name=["\']generator["\'][^>]+content=["\']([^"\']+)["\']',
                html,
                re.IGNORECASE,
            )
            if generator_match:
                findings.append(("Meta generator", generator_match.group(1)))

            lines = f"{GREEN}root@osint-bot{RESET}:{CYAN}~/domain{RESET}$ fingerprint {url}\n\n"
            lines += kv("http_status", str(status)) + "\n\n"

            if not findings:
                lines += f"{YELLOW}no recognizable technology signatures found{RESET}"
            else:
                seen = set()
                for label, value in findings:
                    key = (label, value)
                    if key in seen:
                        continue
                    seen.add(key)
                    lines += kv(label, value) + "\n"

            embed = discord.Embed(
                title="🧩  TECH STACK FINGERPRINT",
                description=f"**Stack for ({url})**\n\n{ansi_block(lines.rstrip())}",
                color=EMBED_COLOR,
            )
            embed.add_field(
                name="⚠️ Note",
                value="Detection is based on public headers and page markup only — sites can mask or spoof these signals.",
                inline=False,
            )
            embed.set_footer(
                text=f"Requested by {ctx.author}",
                icon_url=ctx.author.display_avatar.url,
            )
            await ctx.reply(embed=embed)

    
    @commands.command()
    async def subdomains(self, ctx: commands.Context, domain: str):
        async with ctx.typing():
            found = {}

            
            url = f"https://crt.sh/?q=%25.{domain}&output=json"
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url,
                        headers={"User-Agent": USER_AGENT},
                        timeout=aiohttp.ClientTimeout(total=15),
                    ) as resp:
                        if resp.status == 200:
                            try:
                                data = await resp.json(content_type=None)
                            except Exception:
                                data = []
                        else:
                            data = []
            except Exception:
                data = []

            ct_names = set()
            for entry in data:
                for n in entry.get("name_value", "").split("\n"):
                    n = n.strip().lower()
                    if n and not n.startswith("*.") and n.endswith(domain):
                        ct_names.add(n)

            
            candidates = [f"{sub}.{domain}" for sub in COMMON_SUBDOMAINS]
            resolve_tasks = [resolve_a_record(c) for c in candidates]
            resolved = await asyncio.gather(*resolve_tasks)

            brute_names = {}
            for hostname, ip in zip(candidates, resolved):
                if ip:
                    brute_names[hostname] = ip

            all_names = ct_names | set(brute_names.keys())
            sorted_names = sorted(all_names)

            if not sorted_names:
                await ctx.reply(f"No subdomains discovered for `{domain}`.")
                return

            lines = f"{GREEN}root@osint-bot{RESET}:{CYAN}~/domain{RESET}$ subdomain-scan {domain}\n\n"
            for n in sorted_names[:25]:
                ip_tag = f" {GREY}-> {brute_names[n]}{RESET}" if n in brute_names else ""
                lines += f"{CYAN}{n}{RESET}{ip_tag}\n"
            if len(sorted_names) > 25:
                lines += f"{GREY}... and {len(sorted_names) - 25} more{RESET}\n"

            lines += (
                f"\n{YELLOW}--- summary ---{RESET}\n"
                f"{WHITE}from CT logs: {len(ct_names)}{RESET}\n"
                f"{WHITE}from brute force (resolved): {GREEN}{len(brute_names)}{RESET}\n"
                f"{WHITE}total unique: {GREEN}{len(sorted_names)}{RESET}"
            )

            embed = discord.Embed(
                title="🔍  SUBDOMAIN DISCOVERY",
                description=f"**Subdomains for ({domain})**\n\n{ansi_block(lines.rstrip())}",
                color=EMBED_COLOR,
            )
            embed.add_field(
                name="⚠️ Note",
                value="Brute force only checks a fixed common-name wordlist — this is not exhaustive. CT log names may include retired or unused hosts.",
                inline=False,
            )
            embed.set_footer(
                text=f"Requested by {ctx.author}",
                icon_url=ctx.author.display_avatar.url,
            )
            await ctx.reply(embed=embed)

    
    @commands.command()
    async def robots(self, ctx: commands.Context, domain: str):
        async with ctx.typing():
            if not domain.startswith(("http://", "https://")):
                base = "https://" + domain
            else:
                base = domain

            robots_url = base.rstrip("/") + "/robots.txt"

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        robots_url,
                        headers={"User-Agent": USER_AGENT},
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as resp:
                        if resp.status != 200:
                            await ctx.reply(f"No `robots.txt` found at `{robots_url}` (HTTP `{resp.status}`).")
                            return
                        text = await resp.text(errors="ignore")
            except Exception as e:
                await ctx.reply(f"Couldn't fetch robots.txt: `{e}`")
                return

            disallowed = []
            sitemaps = []
            for line in text.splitlines():
                line = line.strip()
                if line.lower().startswith("disallow:"):
                    path = line.split(":", 1)[1].strip()
                    if path:
                        disallowed.append(path)
                elif line.lower().startswith("sitemap:"):
                    sitemaps.append(line.split(":", 1)[1].strip())

            lines = f"{GREEN}root@osint-bot{RESET}:{CYAN}~/domain{RESET}$ cat robots.txt\n\n"

            if disallowed:
                lines += f"{YELLOW}[Disallowed paths]{RESET}\n"
                for path in disallowed[:20]:
                    lines += f"  {WHITE}{path}{RESET}\n"
                if len(disallowed) > 20:
                    lines += f"  {GREY}... and {len(disallowed) - 20} more{RESET}\n"
            else:
                lines += f"{GREY}no Disallow rules found{RESET}\n"

            if sitemaps:
                lines += f"\n{YELLOW}[Sitemaps]{RESET}\n"
                for sm in sitemaps:
                    lines += f"  {CYAN}{sm}{RESET}\n"

            embed = discord.Embed(
                title="🤖  ROBOTS.TXT",
                description=f"**Rules for ({base})**\n\n{ansi_block(lines.rstrip())}",
                color=EMBED_COLOR,
            )
            embed.add_field(
                name="⚠️ Note",
                value="Disallowed paths are often the most interesting ones (admin panels, staging areas) — but this file is advisory only and doesn't restrict access on its own.",
                inline=False,
            )
            embed.set_footer(
                text=f"Requested by {ctx.author}",
                icon_url=ctx.author.display_avatar.url,
            )
            await ctx.reply(embed=embed)

    
    @commands.command()
    async def typosquat(self, ctx: commands.Context, domain: str):
        async with ctx.typing():
            variants = generate_typo_variants(domain)
            if not variants:
                await ctx.reply("Please provide a domain in the form `example.com`.")
                return

            resolve_tasks = [resolve_a_record(v) for v in variants]
            resolved = await asyncio.gather(*resolve_tasks)

            registered = [(v, ip) for v, ip in zip(variants, resolved) if ip]

            lines = f"{GREEN}root@osint-bot{RESET}:{CYAN}~/domain{RESET}$ typosquat-check {domain}\n\n"

            if not registered:
                lines += f"{GREEN}no registered typo variants found{RESET}"
            else:
                for v, ip in registered:
                    lines += f"{RED}[REGISTERED]{RESET}  {WHITE}{v:<28}{RESET} {GREY}-> {ip}{RESET}\n"

            lines += (
                f"\n{YELLOW}--- summary ---{RESET}\n"
                f"{WHITE}variants checked: {len(variants)}{RESET}\n"
                f"{WHITE}registered: {RED if registered else GREEN}{len(registered)}{RESET}"
            )

            embed = discord.Embed(
                title="🎭  TYPOSQUAT CHECK",
                description=f"**Typo variants of ({domain})**\n\n{ansi_block(lines.rstrip())}",
                color=EMBED_COLOR,
            )
            embed.add_field(
                name="⚠️ Note",
                value="A registered variant isn't automatically malicious — some brands legitimately register their own typo domains defensively. Investigate before assuming bad intent.",
                inline=False,
            )
            embed.set_footer(
                text=f"Requested by {ctx.author}",
                icon_url=ctx.author.display_avatar.url,
            )
            await ctx.reply(embed=embed)

    
    @commands.command()
    async def netping(self, ctx: commands.Context, host: str):
        async with ctx.typing():
            clean_host = re.sub(r"^https?://", "", host).split("/")[0]

            try:
                resolved_ip = socket.gethostbyname(clean_host)
            except socket.gaierror:
                await ctx.reply(f"Couldn't resolve `{clean_host}` — check the hostname/IP and try again.")
                return

            args = build_ping_args(clean_host)

            try:
                proc = await asyncio.create_subprocess_exec(
                    *args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=PING_TIMEOUT_SECONDS
                )
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                except Exception:
                    pass
                await ctx.reply(f"Ping to `{clean_host}` timed out after {PING_TIMEOUT_SECONDS}s.")
                return
            except FileNotFoundError:
                await ctx.reply(
                    "The `ping` command isn't available on this system/container. "
                    "This command needs a host OS with ICMP ping installed."
                )
                return
            except Exception as e:
                await ctx.reply(f"Couldn't run ping: `{e}`")
                return

            output = stdout.decode(errors="ignore") or stderr.decode(errors="ignore")
            stats = parse_ping_output(output)

            lines = f"{GREEN}root@osint-bot{RESET}:{CYAN}~/domain{RESET}$ ping {clean_host} ({resolved_ip})\n\n"

            if stats["sent"] is not None:
                sent = stats["sent"]
                received = stats["received"] or 0
                loss = stats["loss_pct"] if stats["loss_pct"] is not None else round(100 * (1 - received / sent)) if sent else 100
                loss_color = GREEN if loss == 0 else (YELLOW if loss < 50 else RED)

                lines += kv("sent", str(sent)) + "\n"
                lines += kv("received", str(received)) + "\n"
                lines += kv("packet_loss", f"{loss_color}{loss}%{RESET}") + "\n"

                if stats["avg_ms"] is not None:
                    avg = stats["avg_ms"]
                    lines += kv("min_latency", f"{stats['min_ms']:.0f}ms" if stats["min_ms"] is not None else "N/A") + "\n"
                    lines += kv("avg_latency", f"{ping_latency_color(avg)}{avg:.0f}ms{RESET}") + "\n"
                    lines += kv("max_latency", f"{stats['max_ms']:.0f}ms" if stats["max_ms"] is not None else "N/A")
                else:
                    lines += f"{GREY}no latency stats available (host may be unreachable){RESET}"
            else:
                lines += f"{RED}couldn't parse ping results — host may be unreachable or blocking ICMP{RESET}"

            embed = discord.Embed(
                title="🌐  NETWORK PING",
                description=f"**Real ICMP ping to ({clean_host})**\n\n{ansi_block(lines.rstrip())}",
                color=EMBED_COLOR,
            )
            embed.add_field(
                name="⚠️ Note",
                value="Some servers/firewalls block ICMP entirely and will always show 100% loss here even if the site is fully reachable over HTTP — this only tests raw ping, not web availability.",
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
    await bot.add_cog(Domain(bot))