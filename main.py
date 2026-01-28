from datetime import datetime
from typing import Dict, Optional

import discord
from discord.abc import Messageable
from discord.ext import commands, tasks
from discord.utils import escape_mentions
from config import TOKEN, ALERT_CHANNEL
from metrics import get_remote_metrics, get_local_metrics
from ui import create_embed
from brain import get_bitty_response, reset_conversation, get_usage_snapshot

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='bit ', intents=intents)

DIGEST_INTERVAL_HOURS = 3

RESET_KEYWORDS = {"reset", "forget", "hapus"}


def format_usage_message(usage_stats: Optional[Dict[str, int]]) -> Optional[str]:
    if not usage_stats:
        return None
    last_prompt = usage_stats.get('last_prompt_tokens', 0)
    last_completion = usage_stats.get('last_completion_tokens', 0)
    last_total = usage_stats.get('last_total_tokens', 0)
    session_total = usage_stats.get('session_total_tokens', 0)
    session_prompt = usage_stats.get('session_prompt_tokens', 0)
    session_completion = usage_stats.get('session_completion_tokens', 0)
    requests = usage_stats.get('requests', 0)

    return (
        f"💳 Kuota Groq (req ke-{requests}): +{last_prompt} prompt / +{last_completion} jawaban "
        f"= {last_total} token. Total sesi: {session_prompt} prompt + {session_completion} jawaban "
        f"= {session_total} token."
    )


def _safe_float(value: object) -> Optional[float]:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _format_temp_text(value: object) -> str:
    temp_val = _safe_float(value)
    if temp_val is None:
        return str(value)
    return f"{temp_val:.1f}°C"


def _log(message: str) -> None:
    timestamp = datetime.now().isoformat(timespec='seconds')
    print(f"[{timestamp}] {message}")


async def _get_alert_channel() -> Optional[Messageable]:
    if ALERT_CHANNEL is None:
        _log("ALERT_CHANNEL belum di-set, skip pengiriman.")
        return None

    channel = bot.get_channel(ALERT_CHANNEL)
    if isinstance(channel, Messageable):
        return channel

    try:
        fetched = await bot.fetch_channel(ALERT_CHANNEL)
    except discord.DiscordException as exc:
        _log(f"Gagal fetch ALERT_CHANNEL {ALERT_CHANNEL}: {exc}")
        return None

    if isinstance(fetched, Messageable):
        return fetched

    _log(f"Channel {ALERT_CHANNEL} bukan Messageable, skip pengiriman.")
    return None

@tasks.loop(seconds=60)
async def check_alerts():
    if not bot.is_ready():
        return
    channel = await _get_alert_channel()
    if channel is None:
        return
    remote = get_remote_metrics()
    local = get_local_metrics()
    r_temp = remote.get('temp')
    l_temp = local.get('temp')

    if isinstance(r_temp, (int, float)) and r_temp > 75:
        await channel.send(f"⚠️ **ALERT: X555BP Overheat!** ({r_temp}°C)")

    l_temp_val = _safe_float(l_temp)

    if l_temp_val and l_temp_val > 65:
        await channel.send(f"⚠️ **ALERT: Bitty Overheat!** ({l_temp_val}°C)")

@tasks.loop(hours=DIGEST_INTERVAL_HOURS)
async def scheduled_digest():
    if not bot.is_ready():
        return
    channel = await _get_alert_channel()
    if channel is None:
        return

    remote = get_remote_metrics()
    local = get_local_metrics()

    embed = create_embed(
        remote.get('temp'),
        remote.get('ram_used_gb', 0.0),
        local.get('temp'),
        local.get('ram_used_gb', 0.0),
        local.get('ram_total_gb', 0.0),
        local.get('disk_percent', 0.0)
    )
    embed.title = f"🛰️ Bitty Digest {DIGEST_INTERVAL_HOURS} Jam"
    embed.set_footer(text=f"⏱️ Digest | Admin: Octa | Next +{DIGEST_INTERVAL_HOURS} jam")

    summary_text = (
        f"📬 **Ringkasan otomatis tiap {DIGEST_INTERVAL_HOURS} jam**\n"
        f"• Server: {_format_temp_text(remote.get('temp'))}, RAM {remote.get('ram_used_gb', 0.0):.2f} GB, CPU {remote.get('cpu_percent', 'n/a')}%\n"
        f"• Raspi: {_format_temp_text(local.get('temp'))}, RAM {local.get('ram_used_gb', 0.0):.2f}/{local.get('ram_total_gb', 0.0):.1f} GB, Disk {local.get('disk_percent', 0.0)}%"
    )

    await channel.send(summary_text, embed=embed)
    _log("Digest berkala berhasil dikirim.")

@bot.command()
async def tanya(ctx, *, pesan):
    remote = get_remote_metrics()
    local = get_local_metrics()
    jawaban, _ = get_bitty_response(ctx.author.id, pesan, remote, local)
    await ctx.send(jawaban)

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    bot_user = bot.user
    if bot_user and bot_user in message.mentions:
        content = message.content
        for mention in message.mentions:
            if mention == bot_user:
                content = content.replace(mention.mention, '').strip()

        if not content:
            await message.channel.send('Tag gue sambil tulis pertanyaan ya, Ta!')
        elif content.lower().split()[0] in RESET_KEYWORDS:
            reset_conversation(message.author.id)
            await message.channel.send('🧹 Obrolan kita udah gue reset. Gas lagi?')
        else:
            remote = get_remote_metrics()
            local = get_local_metrics()
            jawaban, _ = get_bitty_response(
                message.author.id,
                escape_mentions(content),
                remote,
                local
            )
            await message.channel.send(jawaban, reference=message)
        return

    await bot.process_commands(message)

@bot.command()
async def reset(ctx):
    reset_conversation(ctx.author.id)
    await ctx.send("🧹 Memori obrolan kita udah aku hapus. Mau bahas apa lagi nih?")


@bot.command(name='token')
async def token_usage(ctx):
    stats = get_usage_snapshot(ctx.author.id)
    summary = format_usage_message(stats)
    if summary:
        await ctx.send(summary)
    else:
        await ctx.send("Belum ada token yang kepake di sesi lo, Ta. Ngobrol dulu yuk!")

@bot.event
async def on_ready():
    if not check_alerts.is_running():
        check_alerts.start()
    if not scheduled_digest.is_running():
        scheduled_digest.start()
    print('Bitty Guard is Online!')

if not TOKEN:
    raise RuntimeError('DISCORD_TOKEN belum di-set di environment (.env)')

bot.run(TOKEN)
