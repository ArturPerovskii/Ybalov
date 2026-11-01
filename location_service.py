
import requests


def search_locations(query):
    response = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={
            "name": query,
            "count": 10,
            "language": "ru",
            "format": "json"
        },
        timeout=15
    )

    response.raise_for_status()

    data = response.json()
    results = []

    for item in data.get("results", []):
        parts = [
            item.get("name"),
            item.get("admin1"),
            item.get("country")
        ]

        results.append({
            "name": ", ".join(
                part for part in parts if part
            ),
            "latitude": item["latitude"],
            "longitude": item["longitude"],
            "timezone": item.get("timezone", "UTC")
        })

    return results
