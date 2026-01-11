import discord
from discord.ext import commands, tasks
import asyncio
from config import TOKEN, ALERT_CHANNEL
from metrics import get_remote_metrics, get_local_metrics
from ui import create_embed
from brain import get_bitty_response

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='bit ', intents=intents)

@tasks.loop(seconds=60)
async def check_alerts():
    if not bot.is_ready(): return
    channel = bot.get_channel(ALERT_CHANNEL)
    if not channel: return
    r_temp, _ = get_remote_metrics()
    l_temp, _, _, _ = get_local_metrics()
    if isinstance(r_temp, (int, float)) and r_temp > 75:
        await channel.send(f"⚠️ **ALERT: X555BP Overheat!** ({r_temp}°C)")
    if float(l_temp) > 65:
        await channel.send(f"⚠️ **ALERT: Bitty Overheat!** ({l_temp}°C)")

@bot.command()
async def tanya(ctx, *, pesan):
    r_temp, r_ram = get_remote_metrics()
    l_temp, _, _, l_disk = get_local_metrics()
    jawaban = get_bitty_response(ctx.author.id, pesan, r_temp, r_ram, l_temp, l_disk)
    await ctx.send(jawaban)

@bot.command()
async def reset(ctx):
    from brain import conversation_history
    if ctx.author.id in conversation_history:
        conversation_history[ctx.author.id] = []
        await ctx.send("🧹 Memori obrolan kita udah gue hapus. Mau bahas apa lagi, Octa?")
    else:
        await ctx.send("Gue emang lagi nggak inget apa-apa soal lu, Ta. Ngobrol dulu yuk!")

@bot.event
async def on_ready():
    check_alerts.start()
    print(f'Bitty Guard is Online!')

bot.run(TOKEN)
