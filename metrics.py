import requests
import psutil
import os
from config import BASE_URL

def get_remote_metrics():
    try:
        temp_url = f"{BASE_URL}/api/v1/data?chart=sensors.temperature_k10temp-pci-00c3_temp1_input&after=-1&format=json"
        ram_url = f"{BASE_URL}/api/v1/data?chart=system.ram&after=-1&format=json"
        temp_r = requests.get(temp_url, timeout=3).json()['data'][0][1]
        ram_r = requests.get(ram_url, timeout=3).json()
        ram_used = ram_r['data'][0][1] / 1024
        return temp_r, ram_used
    except:
        return "Offline", 0

def get_local_metrics():
    temp = os.popen("vcgencmd measure_temp").readline().replace("temp=","").replace("'C\n","")
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    return temp, ram.used / (1024**3), ram.total / (1024**3), disk.percent
