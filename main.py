import discord
from discord.abc import Messageable
from discord.ext import commands, tasks
from discord.utils import escape_mentions
from config import TOKEN, ALERT_CHANNEL
from metrics import get_remote_metrics, get_local_metrics
from brain import get_bitty_response

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='bit ', intents=intents)

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

@bot.command()
async def tanya(ctx, *, pesan):
    r_temp, r_ram = get_remote_metrics()
    l_temp, _, _, l_disk = get_local_metrics()
    jawaban = get_bitty_response(ctx.author.id, pesan, r_temp, r_ram, l_temp, l_disk)
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
        else:
            r_temp, r_ram = get_remote_metrics()
            l_temp, _, _, l_disk = get_local_metrics()
            jawaban = get_bitty_response(message.author.id, escape_mentions(content), r_temp, r_ram, l_temp, l_disk)
            await message.channel.send(jawaban, reference=message)
        return

    await bot.process_commands(message)

@bot.command()
async def reset(ctx):
    from brain import conversation_history
    if ctx.author.id in conversation_history:
        conversation_history[ctx.author.id] = []
        await ctx.send("🧹 Memori obrolan kita udah aku hapus. Mau bahas apa lagi nih?")
    else:
        await ctx.send("Pikiran kosong, aman Ta. Ngobrol dulu yuk!")

@bot.event
async def on_ready():
    check_alerts.start()
    print('Bitty Guard is Online!')

if not TOKEN:
    raise RuntimeError('DISCORD_TOKEN belum di-set di environment (.env)')

bot.run(TOKEN)
