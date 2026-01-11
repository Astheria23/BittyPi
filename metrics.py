from __future__ import annotations

import copy
import os
import time
from typing import Dict, List, Optional

import psutil
import requests

from config import BASE_URL

NETDATA_TIMEOUT = 4
REMOTE_DEFAULT = {
    "temp": "Offline",
    "ram_used_gb": 0.0,
    "ram_total_gb": None,
    "cpu_percent": None,
    "load": (None, None, None),
    "swap": {"used_gb": None, "total_gb": None},
    "net": {"in_kbps": None, "out_kbps": None},
    "top_cpu": [],
    "top_mem": []
}

LOCAL_DEFAULT = {
    "temp": "Unknown",
    "cpu_percent": None,
    "load": (None, None, None),
    "ram_used_gb": None,
    "ram_total_gb": None,
    "swap": {"used_gb": None, "total_gb": None},
    "disk_percent": None,
    "net": {"in_kbps": None, "out_kbps": None},
    "top_cpu": [],
    "top_mem": []
}

_REMOTE_TEMP_CHART = "sensors.temperature_k10temp-pci-00c3_temp1_input"
_REMOTE_RAM_CHART = "system.ram"
_REMOTE_CPU_CHART = "system.cpu"
_REMOTE_LOAD_CHART = "system.load"
_REMOTE_SWAP_CHART = "system.swap"
_REMOTE_NET_CHART = "system.net"
_REMOTE_APPS_CPU_CHART = "apps.cpu"
_REMOTE_APPS_MEM_CHART = "apps.mem"

_local_net_snapshot: Optional[Dict[str, float]] = None


def _safe_netdata_request(params: Dict[str, str]) -> Optional[Dict]:
    if not BASE_URL:
        return None
    try:
        response = requests.get(f"{BASE_URL}/api/v1/data", params=params, timeout=NETDATA_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def _latest_chart_values(chart: str, after: int = -60, points: int = 1) -> Dict[str, float]:
    payload = _safe_netdata_request({
        "chart": chart,
        "after": str(after),
        "format": "json",
        "points": str(points),
        "group": "average"
    })
    if not payload or not payload.get("data"):
        return {}
    labels = payload.get("labels", [])[1:]
    values = payload["data"][-1][1:]
    return dict(zip(labels, values))


def _latest_chart_value(chart: str) -> Optional[float]:
    payload = _safe_netdata_request({
        "chart": chart,
        "after": "-1",
        "format": "json",
        "points": "1"
    })
    if not payload or not payload.get("data"):
        return None
    return payload["data"][0][1]


def _top_dimensions(chart: str, limit: int = 5) -> List[Dict[str, float]]:
    values = _latest_chart_values(chart)
    if not values:
        return []
    sorted_dims = sorted(values.items(), key=lambda item: item[1], reverse=True)
    result = []
    for name, value in sorted_dims[:limit]:
        if value <= 0:
            continue
        result.append({"name": name, "value": value})
    return result


def get_remote_metrics() -> Dict:
    metrics = copy.deepcopy(REMOTE_DEFAULT)
    if not BASE_URL:
        return metrics

    temp_value = _latest_chart_value(_REMOTE_TEMP_CHART)
    if temp_value is not None:
        metrics["temp"] = temp_value

    ram_values = _latest_chart_values(_REMOTE_RAM_CHART)
    if ram_values:
        used_kib = ram_values.get("used", 0)
        other = sum(v for k, v in ram_values.items() if k not in {"time", "used"})
        total_kib = used_kib + other
        metrics["ram_used_gb"] = used_kib / (1024 ** 2)
        metrics["ram_total_gb"] = total_kib / (1024 ** 2) if total_kib else None

    cpu_values = _latest_chart_values(_REMOTE_CPU_CHART)
    if cpu_values:
        active = sum(v for k, v in cpu_values.items() if k.lower() != "idle")
        metrics["cpu_percent"] = round(active, 2)

    load_values = _latest_chart_values(_REMOTE_LOAD_CHART)
    if load_values:
        metrics["load"] = (
            load_values.get("load1"),
            load_values.get("load5"),
            load_values.get("load15")
        )

    swap_values = _latest_chart_values(_REMOTE_SWAP_CHART)
    if swap_values:
        used = swap_values.get("used", 0)
        free = swap_values.get("free", 0)
        total = used + free
        metrics["swap"] = {
            "used_gb": used / (1024 ** 2),
            "total_gb": total / (1024 ** 2) if total else None
        }

    net_values = _latest_chart_values(_REMOTE_NET_CHART)
    if net_values:
        metrics["net"] = {
            "in_kbps": net_values.get("received"),
            "out_kbps": net_values.get("sent")
        }

    cpu_processes = _top_dimensions(_REMOTE_APPS_CPU_CHART)
    mem_processes = _top_dimensions(_REMOTE_APPS_MEM_CHART)
    if mem_processes:
        for proc in mem_processes:
            proc["value"] = proc["value"] / 1024  # convert KiB to MiB

    metrics["top_cpu"] = cpu_processes
    metrics["top_mem"] = mem_processes
    return metrics


def _read_local_temp() -> str:
    temp_raw = os.popen("vcgencmd measure_temp").readline()
    return temp_raw.replace("temp=", "").replace("'C\n", "") or "Unknown"


def _local_net_rates() -> Dict[str, float]:
    global _local_net_snapshot
    counters = psutil.net_io_counters()
    now = time.time()
    if _local_net_snapshot:
        delta = now - _local_net_snapshot["time"]
        if delta > 0:
            in_rate = (counters.bytes_recv - _local_net_snapshot["recv"]) / delta / 1024
            out_rate = (counters.bytes_sent - _local_net_snapshot["sent"]) / delta / 1024
        else:
            in_rate = out_rate = 0.0
    else:
        in_rate = out_rate = 0.0

    _local_net_snapshot = {
        "time": now,
        "recv": counters.bytes_recv,
        "sent": counters.bytes_sent
    }
    return {"in_kbps": round(in_rate, 2), "out_kbps": round(out_rate, 2)}


def _collect_local_processes(limit: int = 5) -> Dict[str, List[Dict[str, float]]]:
    processes = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            proc.cpu_percent(interval=None)
            processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    time.sleep(0.15)
    stats = []
    for proc in processes:
        try:
            cpu = proc.cpu_percent(interval=None)
            mem = proc.memory_info().rss / (1024 ** 2)
            stats.append({
                "name": proc.info.get('name') or f"pid-{proc.pid}",
                "cpu": cpu,
                "memory": mem
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    top_cpu = sorted(stats, key=lambda item: item['cpu'], reverse=True)[:limit]
    top_mem = sorted(stats, key=lambda item: item['memory'], reverse=True)[:limit]
    return {"top_cpu": top_cpu, "top_mem": top_mem}


def get_local_metrics() -> Dict:
    metrics = copy.deepcopy(LOCAL_DEFAULT)

    metrics["temp"] = _read_local_temp()
    metrics["cpu_percent"] = psutil.cpu_percent(interval=0.2)
    try:
        metrics["load"] = os.getloadavg()
    except OSError:
        metrics["load"] = (None, None, None)

    ram = psutil.virtual_memory()
    metrics["ram_used_gb"] = ram.used / (1024 ** 3)
    metrics["ram_total_gb"] = ram.total / (1024 ** 3)

    swap = psutil.swap_memory()
    metrics["swap"] = {
        "used_gb": swap.used / (1024 ** 3),
        "total_gb": swap.total / (1024 ** 3) if swap.total else None
    }

    disk = psutil.disk_usage('/')
    metrics["disk_percent"] = disk.percent
    metrics["net"] = _local_net_rates()

    proc_stats = _collect_local_processes()
    metrics["top_cpu"] = proc_stats["top_cpu"]
    metrics["top_mem"] = proc_stats["top_mem"]

    return metrics