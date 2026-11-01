
import requests

API_URL = "https://api.open-meteo.com/v1/forecast"


def get_weather(latitude, longitude, timezone):
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "pressure_msl,temperature_2m",
        "timezone": timezone
    }

    response = requests.get(
        API_URL,
        params=params,
        timeout=20
    )

    response.raise_for_status()

    data = response.json()
    current = data["current"]

    return {
        "timestamp": current["time"],
        "pressure": current["pressure_msl"],
        "temperature": current["temperature_2m"]
    }
