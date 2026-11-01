
import cloud_api

history = cloud_api.get_history(limit=10)

print("Получено измерений:", len(history))

for item in history:
    print(
        item["timestamp"],
        item["pressure"],
        item["temperature"]
    )
