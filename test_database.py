
import database

database.initialize()

test_records = [
    {
        "timestamp": "2026-11-01T20:00:00.000Z",
        "pressure": 1030.5,
        "temperature": 8.5
    },
    {
        "timestamp": "2026-11-01T20:15:00.000Z",
        "pressure": 1030.8,
        "temperature": 8.2
    }
]

database.save_weather_batch(test_records)

history = database.get_history()

print("Всего записей:", len(history))
print("Последние записи:")

for record in history[-2:]:
    print(record)
