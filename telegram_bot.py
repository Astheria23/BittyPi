import requests
import time

# Pake ID sensor AMD k10temp yang tadi kamu dapet
CHART_ID = "sensors.temperature_k10temp-pci-00c3_temp1_input"
URL = f"https://monitor.remotion.web.id/api/v1/data?chart={CHART_ID}&after=-1&format=json"

def get_temp():
    try:
        response = requests.get(URL)
        data = response.json()

        # Bedah datanya: baris pertama [0], kolom kedua [1]
        temp_value = data['data'][0][1]
        return temp_value
    except Exception as e:
        return f"Error: {e}"

print("--- Memulai Monitoring Suhu X555BP ---")
while True:
    suhu = get_temp()
    print(f"Suhu CPU Saat Ini: {suhu} °C")

    # Refresh tiap 2 detik biar gak menuhin log
    time.sleep(2)
