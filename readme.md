# osint-bot

A terminal/hacker-themed OSINT (open-source intelligence) Discord bot built with `discord.py`. Every command output is styled like a fake shell session using Discord's `ansi` code blocks — green prompts, colored status tags, the works.

![status](https://img.shields.io/badge/status-active-brightgreen) ![python](https://img.shields.io/badge/python-3.13-blue) ![discord.py](https://img.shields.io/badge/discord.py-2.3%2B-blueviolet)

---

## ✨ Features

- **Domain & IP recon** — WHOIS, DNS records, IP geolocation, Certificate Transparency log search, tech-stack fingerprinting, subdomain discovery, robots.txt parsing, typosquat detection, real ICMP ping
- **Username recon** — scan a handle across 12 major platforms
- **Social media recon** — check a name/handle across 10 social platforms plus a Discord shared-server lookup
- **Email recon** — format/MX validation, breach database checks (HIBP)
- **Image recon** — reverse image search links, EXIF metadata extraction (including GPS)
- **Threat intel** — IP reputation (AbuseIPDB), file hash scanning (VirusTotal), favicon hash pivoting (Shodan)
- **Archive & leaks** — Wayback Machine snapshot history, public paste-dump search
- **Crypto recon** — public BTC/ETH wallet balance lookups
- **Bot info** — live uptime, system resource usage, command/module counts, changelog
- **Terminal-styled `.help` panel** with a category dropdown
- **Owner-only controls** — safe shutdown/restart with confirmation prompts
- **Global error handling** with a "did you mean?" suggestion system for mistyped commands

---

## 📁 Project structure

```
.
├── bash.py              # Entry point — bot setup, cog loader, global error handlers
├── cogs/
│   ├── general.py        # .ping, .help, .botinfo
│   ├── domain.py          # .whois, .dns, .ipinfo, .certs, .techstack,
│   │                       # .subdomains, .robots, .typosquat, .netping
│   ├── username.py        # .username, .namecheck
│   ├── social.py           # .social
│   ├── email.py             # .emailcheck, .breach
│   ├── image.py              # .reverse, .exif
│   ├── threat.py              # .iprep, .hashcheck, .favhash
│   ├── archive.py              # .wayback, .pastesearch
│   ├── crypto.py                # .wallet
│   ├── owner.py                  # .shutdown, .restart
│   └── errors.py                  # global error handling + did-you-mean UI
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🚀 Setup

### 1. Clone and install dependencies

```bash
git clone https://github.com/himanshurwtt/osint-bot.git
cd osint-bot
pip install -r requirements.txt
```

### 2. Create your `.env`

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

```env
DISCORD_TOKEN=your_bot_token_here
OWNER_ID=your_discord_user_id

# Optional — commands work without these, just with reduced functionality
HIBP_API_KEY=
GEOAPIFY_API_KEY=
ABUSEIPDB_API_KEY=
VIRUSTOTAL_API_KEY=
SHODAN_API_KEY=
RAPIDAPI_KEY=
```

**Never commit your `.env` file.** It's already covered by `.gitignore`.

### 3. Enable required Discord intents

In the [Discord Developer Portal](https://discord.com/developers/applications) → your app → **Bot** tab → enable:
- **Message Content Intent**
- **Server Members Intent**

### 4. Run it

```bash
python bash.py
```

---

## 🔑 API keys — what you need and why

Every command runs without any API key **except** the ones below, which show a clear setup message instead of failing if the key is missing:

| Command | Service | Free tier? | Get a key |
|---|---|---|---|
| `.breach` | Have I Been Pwned | ❌ paid only (~$3.50/mo) | https://haveibeenpwned.com/API/Key |
| `.iprep` | AbuseIPDB | ✅ 1,000 checks/day | https://www.abuseipdb.com/api |
| `.hashcheck` | VirusTotal | ✅ 500 lookups/day | https://www.virustotal.com/gui/join-us |
| `.favhash` (Shodan pivot) | Shodan | ✅ limited free credits | https://account.shodan.io/register |
| `.pastesearch` | BreachDirectory (via RapidAPI) | ✅ limited free tier | https://rapidapi.com/rohan-patra/api/breachdirectory |
| `.ipinfo` (map image) | Geoapify | ✅ free tier | https://www.geoapify.com/ |

Everything else (`.whois`, `.dns`, `.certs`, `.techstack`, `.subdomains`, `.robots`, `.typosquat`, `.netping`, `.username`, `.namecheck`, `.social`, `.emailcheck`, `.reverse`, `.exif`, `.wayback`, `.wallet`) works with zero configuration.

---

## 📖 Command reference

Run `.help` in Discord for the full interactive panel. Quick summary:

<details>
<summary><strong>🌐 General</strong></summary>

| Command | Description |
|---|---|
| `.ping` | Check the bot's latency |
| `.help` | Interactive help panel |
| `.botinfo` | Bot stats, system info, developer credits |

</details>

<details>
<summary><strong>🖥️ Domain & IP</strong></summary>

| Command | Description |
|---|---|
| `.whois <domain>` | WHOIS registration info |
| `.dns <domain>` | DNS records (A, AAAA, MX, NS, TXT) |
| `.ipinfo <ip>` | Geolocation and ISP info |
| `.certs <domain>` | Certificate Transparency log search (crt.sh) |
| `.techstack <url>` | Fingerprint a site's tech stack |
| `.subdomains <domain>` | Subdomain discovery (CT logs + brute force) |
| `.robots <domain>` | Parse robots.txt / sitemap.xml |
| `.typosquat <domain>` | Check registered typo variants |
| `.netping <host>` | Real ICMP ping (not simulated) |

</details>

<details>
<summary><strong>🔎 Username & 📱 Social</strong></summary>

| Command | Description |
|---|---|
| `.username <name>` | Scan 12 platforms for a handle |
| `.namecheck <name>` | Same as `.username` |
| `.social <name>` | Scan 10 social platforms + Discord shared-server lookup |

</details>

<details>
<summary><strong>📧 Email & 🖼️ Image</strong></summary>

| Command | Description |
|---|---|
| `.emailcheck <email>` | Format + MX record validation |
| `.breach <email>` | Breach database check |
| `.reverse <image_url>` | Reverse image search links |
| `.exif <image_url>` | EXIF metadata extraction |

</details>

<details>
<summary><strong>🛡️ Threat Intel, 🗄️ Archive, 💰 Crypto</strong></summary>

| Command | Description |
|---|---|
| `.iprep <ip>` | IP abuse/reputation check |
| `.hashcheck <hash>` | File hash malware check |
| `.favhash <url>` | Favicon hash + Shodan pivot |
| `.wayback <url>` | Wayback Machine snapshot history |
| `.pastesearch <keyword>` | Public paste dump search |
| `.wallet <address>` | BTC/ETH wallet balance lookup |

</details>

<details>
<summary><strong>🛡️ Owner-only</strong></summary>

| Command | Description |
|---|---|
| `.shutdown` | Safely shut down the bot |
| `.restart` | Restart the bot process |

</details>

---

## ⚠️ Responsible use

This bot only surfaces **publicly available information** — WHOIS records, public DNS, public social profiles, public blockchain data, public breach databases, and metadata embedded in files you already have access to. It doesn't scrape private data, bypass authentication, or target specific individuals without their knowledge.

Use it for legitimate purposes: security research, protecting your own digital footprint, journalism, brand protection, or general curiosity about public infrastructure. Don't use it to stalk, harass, or dox anyone.

---

## 🛠️ Built with

- [discord.py](https://github.com/Rapptz/discord.py)
- [aiohttp](https://github.com/aio-libs/aiohttp)
- [dnspython](https://github.com/rthalley/dnspython)
- [python-whois](https://github.com/richardpenman/whois)
- [Pillow](https://github.com/python-pillow/Pillow)
- [mmh3](https://github.com/hajimes/mmh3)
- [psutil](https://github.com/giampaolo/psutil)

---

## 👤 Developer

**Himanshu Rawat**
- Discord: `geek7`
- GitHub: [@himanshurwtt](https://github.com/himanshurwtt)
- Instagram: [@himanshuurwt](https://instagram.com/himanshuurwt)

---

## 📄 License

Add a license of your choice (MIT is a common default for personal projects like this — see [choosealicense.com](https://choosealicense.com/)).