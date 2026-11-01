
import requests

WORKER_URL = "https://weather-monitor.happywolffan.workers.dev"


def get_history(limit=10000):
    url = f"{WORKER_URL}/api/history"

    response = requests.get(
        url,
        params={"limit": limit},
        timeout=20
    )

    response.raise_for_status()

    result = response.json()

    return result["data"]
