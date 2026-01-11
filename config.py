import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
BASE_URL = os.getenv('NETDATA_BASE_URL')
GROQ_KEY = os.getenv('GROQ_API_KEY')
MODEL_NAME = os.getenv('MODEL_NAME', 'llama-3.3-70b-versatile')

# Alert Channel ID
raw_channel_id = os.getenv('ALERT_CHANNEL_ID')
try:
    ALERT_CHANNEL = int(raw_channel_id) if raw_channel_id else 0
except ValueError:
    print(f"❌ Error: ALERT_CHANNEL_ID di .env bukan angka: '{raw_channel_id}'")
    ALERT_CHANNEL = 0
