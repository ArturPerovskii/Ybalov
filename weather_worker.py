
import threading

from PySide6.QtCore import QThread, Signal

import database
import weather_api


class WeatherWorker(QThread):
    """
    Фоновый сборщик погодных данных.

    Получает данные каждые 15 минут,
    сохраняет их в SQLite и отправляет
    сигнал интерфейсу после обновления.
    """

    weather_updated = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, location, interval=15 * 60):
        super().__init__()

        self.location = location
        self.interval = interval

        self.stop_event = threading.Event()

    def run(self):
        print("Weather worker started")

        while not self.stop_event.is_set():

            try:
                weather = weather_api.get_weather(
                    self.location["latitude"],
                    self.location["longitude"],
                    self.location["timezone"]
                )

                database.save_weather(
                    weather["timestamp"],
                    weather["pressure"],
                    weather["temperature"]
                )

                self.weather_updated.emit(weather)

            except Exception as error:
                self.error_occurred.emit(str(error))

            # Ожидание следующего обновления.
            # Ожидание можно прервать при завершении приложения.
            self.stop_event.wait(self.interval)

        print("Weather worker stopped")

    def stop(self):
        self.stop_event.set()
