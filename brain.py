import asyncio
import edge_tts
from groq import Groq
from config import GROQ_KEY, MODEL_NAME

client = Groq(api_key=GROQ_KEY)
conversation_history = {}
conversation_usage = {}

def transcribe_audio(filename: str) -> str:
    with open(filename, "rb") as file:
        transcription = client.audio.transcriptions.create(
            file=(filename, file.read()),
            model="whisper-large-v3",
            response_format="json"
        )
    return transcription.text

async def speak_response(text: str, output_file: str = "response.mp3") -> str:
    # Voice: id-ID-ArdiNeural (Male) or id-ID-GadisNeural (Female)
    communicate = edge_tts.Communicate(text, "id-ID-ArdiNeural")
    await communicate.save(output_file)
    return output_file

def _extract_usage_tokens(usage_obj):
    if not usage_obj:
        return 0, 0, 0
    if isinstance(usage_obj, dict):
        prompt = usage_obj.get('prompt_tokens', 0)
        completion = usage_obj.get('completion_tokens', 0)
        total = usage_obj.get('total_tokens', prompt + completion)
        return prompt or 0, completion or 0, total or 0
    prompt = getattr(usage_obj, 'prompt_tokens', 0)
    completion = getattr(usage_obj, 'completion_tokens', 0)
    total = getattr(usage_obj, 'total_tokens', prompt + completion)
    return prompt or 0, completion or 0, total or 0


def _format_float(value, unit="", precision=1, fallback="unknown"):
    if isinstance(value, (int, float)):
        return f"{value:.{precision}f}{unit}"
    return fallback


def _format_load(load_tuple):
    if not load_tuple:
        return "?/?/?"
    parts = []
    for val in load_tuple:
        parts.append(f"{val:.2f}" if isinstance(val, (int, float)) else "?")
    return "/".join(parts)


def _format_processes(processes, unit="%", precision=1):
    if not processes:
        return "N/A"
    formatted = []
    for proc in processes:
        name = proc.get("name", "?")
        if unit.strip() == "%":
            value = proc.get("value")
            if value is None:
                value = proc.get("cpu")
        else:
            value = proc.get("memory")
            if value is None:
                value = proc.get("value")
        if value is None:
            continue
        formatted.append(f"{name} ({value:.{precision}f}{unit})")
    return ", ".join(formatted) if formatted else "N/A"


def _build_system_context(remote, local):
    remote_temp = remote.get("temp")
    remote_temp_str = f"{remote_temp}°C" if isinstance(remote_temp, (int, float)) else str(remote_temp)
    remote_cpu = _format_float(remote.get("cpu_percent"), unit="%")
    remote_load = _format_load(remote.get("load"))
    remote_ram = _format_float(remote.get("ram_used_gb"), unit="GB")
    remote_swap = remote.get("swap", {})
    remote_swap_str = f"{_format_float(remote_swap.get('used_gb'), 'GB')} / {_format_float(remote_swap.get('total_gb'), 'GB')}"
    remote_net = remote.get("net", {})
    remote_net_str = f"↓{_format_float(remote_net.get('in_kbps'), ' KB/s')} ↑{_format_float(remote_net.get('out_kbps'), ' KB/s')}"
    remote_top_cpu = _format_processes(remote.get("top_cpu"), unit="%")
    remote_top_mem = _format_processes(remote.get("top_mem"), unit=" MB", precision=1)

    local_temp = local.get("temp")
    local_temp_str = f"{local_temp}°C" if isinstance(local_temp, (int, float)) else str(local_temp)
    local_cpu = _format_float(local.get("cpu_percent"), unit="%")
    local_load = _format_load(local.get("load"))
    local_ram = _format_float(local.get("ram_used_gb"), unit="GB")
    local_ram_total = _format_float(local.get("ram_total_gb"), unit="GB")
    local_swap = local.get("swap", {})
    local_swap_str = f"{_format_float(local_swap.get('used_gb'), 'GB')} / {_format_float(local_swap.get('total_gb'), 'GB')}"
    local_net = local.get("net", {})
    local_net_str = f"↓{_format_float(local_net.get('in_kbps'), ' KB/s')} ↑{_format_float(local_net.get('out_kbps'), ' KB/s')}"
    local_disk = _format_float(local.get("disk_percent"), unit="%")
    local_top_cpu = _format_processes(local.get("top_cpu"), unit="%")
    local_top_mem = _format_processes(local.get("top_mem"), unit=" MB", precision=1)

    remote_summary = (
        f"Server: Temp {remote_temp_str}, CPU {remote_cpu}, Load {remote_load}, RAM {remote_ram}, Swap {remote_swap_str}, "
        f"Net {remote_net_str}, Top CPU {remote_top_cpu}, Top RAM {remote_top_mem}."
    )

    local_summary = (
        f"Raspi: Temp {local_temp_str}, CPU {local_cpu}, Load {local_load}, RAM {local_ram}/{local_ram_total}, Swap {local_swap_str}, "
        f"Disk {local_disk}, Net {local_net_str}, Top CPU {local_top_cpu}, Top RAM {local_top_mem}."
    )

    return remote_summary + " " + local_summary


def get_bitty_response(user_id, user_input, remote_metrics, local_metrics, is_alert=False):
    if user_id not in conversation_history:
        conversation_history[user_id] = []

    # Persona Universal Assistant with IoT Capabilities
    system_context = (
        "Kamu adalah Bitty, asisten AI pribadi Octa yang cerdas, ramah, dan serba bisa. "
        "Kamu bisa membantu menjawab berbagai pertanyaan umum, menulis koding, atau sekadar ngobrol santai. "
        "Kamu juga terhubung langsung dengan sensor hardware Octa, jadi kamu bisa memberi info status server kapanpun diminta. "
        "Gunakan gaya bahasa yang natural, santai, dan membantu. "
        "Data IoT Saat Ini: "
        + _build_system_context(remote_metrics, local_metrics)
    )
    
    # Prompt khusus kalau ini adalah inisiatif alert dari bot
    if is_alert:
        r_temp = remote_metrics.get("temp")
        l_temp = local_metrics.get("temp")
        user_input = (
            f"Woi, suhu server lagi tinggi nih (Laptop: {r_temp}C, Raspi: {l_temp}C). "
            "Tegur Octa dengan gaya lo yang galak dan tanya dia lagi ngapain!"
        )

    messages = [{"role": "system", "content": system_context}]
    messages.extend(conversation_history[user_id])
    messages.append({"role": "user", "content": user_input})

    chat_completion = client.chat.completions.create(
        messages=messages,  # type: ignore[arg-type]
        model=MODEL_NAME, # Diambil dari .env
        temperature=0.6
    )
    
    response = chat_completion.choices[0].message.content
    
    # Simpan history
    conversation_history[user_id].append({"role": "user", "content": user_input})
    conversation_history[user_id].append({"role": "assistant", "content": response})

    # Limit history (10 pesan terakhir)
    if len(conversation_history[user_id]) > 10:
        conversation_history[user_id] = conversation_history[user_id][-10:]

    usage_stats = _update_usage(user_id, getattr(chat_completion, 'usage', None))

    return response, usage_stats

def _update_usage(user_id, usage_obj):
    prompt_tokens, completion_tokens, total_tokens = _extract_usage_tokens(usage_obj)
    stats = conversation_usage.setdefault(user_id, {
        'prompt_tokens': 0,
        'completion_tokens': 0,
        'total_tokens': 0,
        'requests': 0
    })

    stats['prompt_tokens'] += prompt_tokens
    stats['completion_tokens'] += completion_tokens
    stats['total_tokens'] += total_tokens or (prompt_tokens + completion_tokens)
    stats['requests'] += 1

    return {
        'last_prompt_tokens': prompt_tokens,
        'last_completion_tokens': completion_tokens,
        'last_total_tokens': total_tokens or (prompt_tokens + completion_tokens),
        'session_prompt_tokens': stats['prompt_tokens'],
        'session_completion_tokens': stats['completion_tokens'],
        'session_total_tokens': stats['total_tokens'],
        'requests': stats['requests']
    }

def reset_conversation(user_id):
    if user_id in conversation_history:
        conversation_history[user_id] = []
    if user_id in conversation_usage:
        del conversation_usage[user_id]

def get_usage_snapshot(user_id):
    stats = conversation_usage.get(user_id)
    if not stats:
        return None
    return stats.copy()