import database

database.initialize()

history = database.get_history()

print(f"Всего записей: {len(history)}")
print()

for timestamp, pressure, temperature in history:
    print(
        f"{timestamp} | "
        f"{pressure} hPa | "
        f"{temperature} °C"
    )