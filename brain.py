from groq import Groq
from config import GROQ_KEY, MODEL_NAME

client = Groq(api_key=GROQ_KEY)
conversation_history = {}

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
        messages=messages,
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

    return response