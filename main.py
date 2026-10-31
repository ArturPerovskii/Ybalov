
import time

import database
import weather_api

INTERVAL = 15 * 60


def main():
    database.initialize()

    print("================================")
    print("       WEATHER MONITOR")
    print("================================")

    while True:
        try:
            weather = weather_api.get_weather()

            database.save_weather(
                weather["timestamp"],
                weather["pressure"],
                weather["temperature"]
            )

            print(
                f'{weather["timestamp"]} | '
                f'{weather["pressure"]} hPa | '
                f'{weather["temperature"]} °C'
            )

        except Exception as error:
            print(f"Error: {error}")

        time.sleep(INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgram stopped")
