
import sys
from datetime import datetime, timedelta

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QLabel,
    QFrame
)
from PySide6.QtCore import QTimer, Qt

import pyqtgraph as pg

import database
import weather_api


class WeatherMonitor(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("WeatherMonitor")
        self.resize(950, 700)

        database.initialize()

        self.setup_ui()

        # Обновление погоды каждые 15 минут
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_weather)
        self.timer.start(15 * 60 * 1000)

        # Сразу получаем погоду при запуске
        self.update_weather()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setSpacing(15)

        title = QLabel("WEATHER MONITOR")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        # Карточки показателей
        cards = QHBoxLayout()

        self.pressure_label = QLabel("-- hPa")
        self.temperature_label = QLabel("-- °C")
        self.status_label = QLabel("Ожидание данных...")

        for label in (self.pressure_label, self.temperature_label):
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("""
                font-size: 28px;
                font-weight: bold;
                padding: 25px;
                background-color: #252a34;
                color: white;
                border-radius: 10px;
            """)
            cards.addWidget(label)

        layout.addLayout(cards)
        layout.addWidget(self.status_label)

        # График давления
        self.pressure_plot = pg.PlotWidget(title="Атмосферное давление")
        self.pressure_plot.setLabel("left", "Давление", units="hPa")
        self.pressure_plot.setLabel("bottom", "Время")
        self.pressure_plot.showGrid(x=True, y=True, alpha=0.3)
        self.pressure_plot.setMinimumHeight(230)
        layout.addWidget(self.pressure_plot)

        self.pressure_curve = self.pressure_plot.plot(
            pen=pg.mkPen("#38a5e5", width=2),
            symbol="o",
            symbolSize=5
        )

        # График температуры
        self.temperature_plot = pg.PlotWidget(title="Температура воздуха")
        self.temperature_plot.setLabel("left", "Температура", units="°C")
        self.temperature_plot.setLabel("bottom", "Время")
        self.temperature_plot.showGrid(x=True, y=True, alpha=0.3)
        self.temperature_plot.setMinimumHeight(230)
        layout.addWidget(self.temperature_plot)

        self.temperature_curve = self.temperature_plot.plot(
            pen=pg.mkPen("#e6a23c", width=2),
            symbol="o",
            symbolSize=5
        )

    def update_weather(self):
        try:
            weather = weather_api.get_weather()

            database.save_weather(
                weather["timestamp"],
                weather["pressure"],
                weather["temperature"]
            )

            self.pressure_label.setText(
                f'{weather["pressure"]:.1f} hPa'
            )

            self.temperature_label.setText(
                f'{weather["temperature"]:.1f} °C'
            )

            self.status_label.setText(
                f'Последнее обновление: {weather["timestamp"]}'
            )

            self.update_graphs()

        except Exception as error:
            self.status_label.setText(f"Ошибка получения данных: {error}")

    def update_graphs(self):
        history = database.get_history()

        if not history:
            return

        now = datetime.now()
        cutoff = now - timedelta(days=1)

        timestamps = []
        pressures = []
        temperatures = []

        for timestamp, pressure, temperature in history:
            dt = datetime.fromisoformat(timestamp)

            if dt.replace(tzinfo=None) < cutoff:
                continue

            timestamps.append(dt.timestamp())
            pressures.append(pressure)
            temperatures.append(temperature)

        self.pressure_curve.setData(timestamps, pressures)
        self.temperature_curve.setData(timestamps, temperatures)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = WeatherMonitor()
    window.show()

    sys.exit(app.exec())
