import discord
import time


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def create_embed(r_temp, r_ram, l_temp, l_ram_u, l_ram_t, l_disk, is_live=False):
    l_temp_val = _to_float(l_temp)
    status_color = discord.Color.green() if (l_temp_val is not None and l_temp_val < 60) else discord.Color.red()
    title = "🛰️ Bitty Live Dashboard" if is_live else "📊 Bitty System Monitoring"
    embed = discord.Embed(title=title, color=status_color)

    server_temp = f"{r_temp}°C" if isinstance(r_temp, (int, float)) else str(r_temp)
    raspi_temp = f"{l_temp_val:.1f}°C" if l_temp_val is not None else str(l_temp)

    embed.add_field(name="💻 Server X555BP", value=f"Temp: {server_temp}\nRAM: {r_ram:.2f} GB", inline=True)
    embed.add_field(name="🤖 Bitty (Raspi)", value=f"Temp: {raspi_temp}\nRAM: {l_ram_u:.2f}/{l_ram_t:.1f}GB\nDisk: {l_disk}%", inline=True)
    embed.set_footer(text=f"{'🔴 LIVE' if is_live else '⏱️ Static'} | {time.strftime('%H:%M:%S')} | Admin: Octa")
    return embed