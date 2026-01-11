import discord
import time

def create_embed(r_temp, r_ram, l_temp, l_ram_u, l_ram_t, l_disk, is_live=False):
    status_color = discord.Color.green() if float(l_temp) < 60 else discord.Color.red()
    title = "🛰️ Bitty Live Dashboard" if is_live else "📊 Bitty System Monitoring"
    embed = discord.Embed(title=title, color=status_color)
    embed.add_field(name="💻 Server X555BP", value=f"Temp: {r_temp}°C\nRAM: {r_ram:.2f} GB", inline=True)
    embed.add_field(name="🤖 Bitty (Raspi)", value=f"Temp: {l_temp}°C\nRAM: {l_ram_u:.2f}/{l_ram_t:.1f}GB\nDisk: {l_disk}%", inline=True)
    embed.set_footer(text=f"{'🔴 LIVE' if is_live else '⏱️ Static'} | {time.strftime('%H:%M:%S')} | Admin: Octa")
    return embed