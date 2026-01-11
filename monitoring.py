import discord
from discord.abc import Messageable
from discord.ext import commands, tasks
import requests
import psutil
import os
import asyncio
import time

from config import TOKEN, ALERT_CHANNEL, BASE_URL

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='bit ', intents=intents)

def get_remote_metrics():
    try:
        temp_url = f"{BASE_URL}/api/v1/data?chart=sensors.temperature_k10temp-pci-00c3_temp1_input&after=-1&format=json"
        ram_url = f"{BASE_URL}/api/v1/data?chart=system.ram&after=-1&format=json"
        
        temp_r = requests.get(temp_url, timeout=3).json()['data'][0][1]
        ram_r = requests.get(ram_url, timeout=3).json()
        ram_used = ram_r['data'][0][1] / 1024
        return temp_r, ram_used
    except Exception:
        return "Offline", 0

def get_local_metrics():
    temp = os.popen("vcgencmd measure_temp").readline().replace("temp=","").replace("'C\n","")
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    return temp, ram.used / (1024**3), ram.total / (1024**3), disk.percent

def create_embed(r_temp, r_ram, l_temp, l_ram_u, l_ram_t, l_disk, is_live=False):
    status_color = discord.Color.green() if float(l_temp) < 60 else discord.Color.red()
    title = "🛰️ Bitty Live Dashboard" if is_live else "📊 Bitty System Monitoring"
    
    embed = discord.Embed(title=title, color=status_color)
    embed.add_field(name="💻 Server X555BP", value=f"Temp: {r_temp}°C\nRAM: {r_ram:.2f} GB", inline=True)
    embed.add_field(name="🤖 Bitty (Raspi)", value=f"Temp: {l_temp}°C\nRAM: {l_ram_u:.2f}/{l_ram_t:.1f}GB\nDisk: {l_disk}%", inline=True)
    
    sync_type = "🔴 LIVE" if is_live else "⏱️ Static"
    embed.set_footer(text=f"{sync_type} | {time.strftime('%H:%M:%S')} | Admin: Octa")
    return embed

@tasks.loop(seconds=60)
async def check_alerts():
    if not bot.is_ready():
        return
    if ALERT_CHANNEL is None:
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

@bot.event
async def on_ready():
    if bot.user:
        print(f'Logged in as {bot.user.name}')
    else:
        print('Logged in, but bot user belum tersedia')
    if not check_alerts.is_running():
        check_alerts.start()

@bot.command()
async def monitor(ctx):
    r_temp, r_ram = get_remote_metrics()
    l_temp, l_ram_u, l_ram_t, l_disk = get_local_metrics()
    await ctx.send(embed=create_embed(r_temp, r_ram, l_temp, l_ram_u, l_ram_t, l_disk))

@bot.command()
async def live(ctx):
    r_temp, r_ram = get_remote_metrics()
    l_temp, l_ram_u, l_ram_t, l_disk = get_local_metrics()
    message = await ctx.send(embed=create_embed(r_temp, r_ram, l_temp, l_ram_u, l_ram_t, l_disk, is_live=True))
    
    while True:
        await asyncio.sleep(10) # Update tiap 10 detik
        r_temp, r_ram = get_remote_metrics()
        l_temp, l_ram_u, l_ram_t, l_disk = get_local_metrics()
        try:
            await message.edit(embed=create_embed(r_temp, r_ram, l_temp, l_ram_u, l_ram_t, l_disk, is_live=True))
        except Exception:
            break # Stop kalau pesan dihapus

if not TOKEN:
    raise RuntimeError('DISCORD_TOKEN belum di-set di environment (.env)')

bot.run(TOKEN)