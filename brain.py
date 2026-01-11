from groq import Groq
from config import GROQ_KEY

client = Groq(api_key=GROQ_KEY)
conversation_history = {}

def get_bitty_response(user_id, user_input, r_temp, r_ram, l_temp, l_disk):
    if user_id not in conversation_history:
        conversation_history[user_id] = []

    # System context yang lebih ketat soal angka hardware
    system_context = (
        f"Kamu adalah Bitty, asisten IoT Octa. Gaya casual, serius, dan blak-blakan. "
        f"PENTING: Gunakan logika hardware Informatika. "
        f"Suhu < 50C = Sangat Adem. 50-70C = Normal. 70-85C = Panas/Load tinggi. > 85C = Bahaya. "
        f"DATA SAAT INI: "
        f"Server X555BP: {r_temp}C, RAM terpakai {r_ram:.2f}GB (dari total 8GB). "
        f"Raspi: {l_temp}C, Disk terisi {l_disk}%. "
         )

    messages = [{"role": "system", "content": system_context}]
    messages.extend(conversation_history[user_id])
    messages.append({"role": "user", "content": user_input})

    chat_completion = client.chat.completions.create(
        messages=messages,
        model="llama-3.3-70b-versatile", # Upgrade ke model 70B yang lebih pinter
        temperature=0.5 # Turunin dikit biar gak terlalu kreatif/halu
    )
    
    response = chat_completion.choices[0].message.content
    conversation_history[user_id].append({"role": "user", "content": user_input})
    conversation_history[user_id].append({"role": "assistant", "content": response})

    if len(conversation_history[user_id]) > 10:
        conversation_history[user_id] = conversation_history[user_id][-10:]

    return response
