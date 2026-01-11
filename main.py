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

@tasks.loop(seconds=60)
async def check_alerts():
    if not bot.is_ready() or ALERT_CHANNEL is None:
        return
    channel = bot.get_channel(ALERT_CHANNEL)
    if not isinstance(channel, Messageable):
        return
    r_temp, _ = get_remote_metrics()
    l_temp, _, _, _ = get_local_metrics()
    if isinstance(r_temp, (int, float)) and r_temp > 75:
        await channel.send(f"⚠️ **ALERT: X555BP Overheat!** ({r_temp}°C)")
    if float(l_temp) > 65:
        await channel.send(f"⚠️ **ALERT: Bitty Overheat!** ({l_temp}°C)")


@tasks.loop(hours=6)
async def scheduled_digest():
    if not bot.is_ready() or ALERT_CHANNEL is None:
        return
    channel = bot.get_channel(ALERT_CHANNEL)
    if not isinstance(channel, Messageable):
        return

    metrics = list(get_remote_metrics()) + list(get_local_metrics())
    r_temp, r_ram, l_temp, l_ram_u, l_ram_t, l_disk = metrics

    embed = create_embed(r_temp, r_ram, l_temp, l_ram_u, l_ram_t, l_disk)
    embed.title = "🛰️ Bitty Digest 6 Jam"
    embed.set_footer(text="⏱️ Digest | Admin: Octa | Next +6 jam")

    summary_text = (
        "📬 **Ringkasan otomatis tiap 6 jam**\n"
        f"• Server: {r_temp}°C, RAM {r_ram:.2f} GB\n"
        f"• Raspi: {l_temp}°C, RAM {l_ram_u:.2f}/{l_ram_t:.1f} GB, Disk {l_disk}%"
    )

    await channel.send(summary_text, embed=embed)

@bot.command()
async def tanya(ctx, *, pesan):
    r_temp, r_ram = get_remote_metrics()
    l_temp, _, _, l_disk = get_local_metrics()
    jawaban, _ = get_bitty_response(ctx.author.id, pesan, r_temp, r_ram, l_temp, l_disk)
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
            r_temp, r_ram = get_remote_metrics()
            l_temp, _, _, l_disk = get_local_metrics()
            jawaban, _ = get_bitty_response(
                message.author.id,
                escape_mentions(content),
                r_temp,
                r_ram,
                l_temp,
                l_disk
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
    check_alerts.start()
    scheduled_digest.start()
    print('Bitty Guard is Online!')

if not TOKEN:
    raise RuntimeError('DISCORD_TOKEN belum di-set di environment (.env)')

bot.run(TOKEN)
