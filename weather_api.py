import requests

API_URL = "https://api.open-meteo.com/v1/forecast"

LATITUDE = 51.99
LONGITUDE = 4.21


def get_weather():

    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "current": "pressure_msl,temperature_2m",
        "timezone": "Europe/Amsterdam"
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
