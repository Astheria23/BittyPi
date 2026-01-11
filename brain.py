from groq import Groq
from config import GROQ_KEY, MODEL_NAME

client = Groq(api_key=GROQ_KEY)
conversation_history = {}
conversation_usage = {}

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


def get_bitty_response(user_id, user_input, r_temp, r_ram, l_temp, l_disk, is_alert=False):
    if user_id not in conversation_history:
        conversation_history[user_id] = []

    # Persona blak-blakan & teknis
    system_context = (
        f"Kamu adalah Bitty, asisten IoT Octa. Gaya bicara casual, blak-blakan, dan anti sugar-coating. "
        f"Gunakan logika hardware: Suhu < 50C Adem, 50-70C Normal, 70-85C Panas, > 85C Bahaya. "
        f"Data saat ini: Laptop {r_temp}C (RAM {r_ram:.2f}GB terpakai), Raspi {l_temp}C (Disk {l_disk}%). "
    )
    
    # Prompt khusus kalau ini adalah inisiatif alert dari bot
    if is_alert:
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