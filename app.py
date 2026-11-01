import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QDialog,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QMenu,
    QSystemTrayIcon,
    QStyle,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction

from weather_worker import WeatherWorker

import pyqtgraph as pg
from pyqtgraph.graphicsItems.DateAxisItem import DateAxisItem

import database
import location_service


SETTINGS_FILE = Path(__file__).with_name("settings.json")


def save_location(location):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as file:
        json.dump(location, file, ensure_ascii=False, indent=4)


def load_location():
    if not SETTINGS_FILE.exists():
        return None

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as file:
            location = json.load(file)

        required = ["name", "latitude", "longitude", "timezone"]
        if all(key in location for key in required):
            return location

    except (OSError, json.JSONDecodeError):
        pass

    return None


class LocationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Выбор местоположения")
        self.resize(450, 400)
        self.selected_location = None

        layout = QVBoxLayout(self)

        title = QLabel("Введите название города:")
        layout.addWidget(title)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Например, Paris")
        self.search_input.returnPressed.connect(self.search)
        layout.addWidget(self.search_input)

        search_button = QPushButton("Найти город")
        search_button.clicked.connect(self.search)
        layout.addWidget(search_button)

        self.results_list = QListWidget()
        self.results_list.itemDoubleClicked.connect(
            lambda item: self.choose()
        )
        layout.addWidget(self.results_list)

        self.choose_button = QPushButton("Выбрать")
        self.choose_button.clicked.connect(self.choose)
        layout.addWidget(self.choose_button)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

    def search(self):
        query = self.search_input.text().strip()
        if not query:
            return

        self.results_list.clear()
        self.status_label.setText("Поиск...")

        try:
            results = location_service.search_locations(query)

            if not results:
                self.status_label.setText("Город не найден.")
                return

            for location in results:
                item = QListWidgetItem(location["name"])
                item.setData(Qt.ItemDataRole.UserRole, location)
                self.results_list.addItem(item)

            self.status_label.setText(
                f"Найдено вариантов: {len(results)}"
            )

        except Exception as error:
            self.status_label.setText(f"Ошибка поиска: {error}")

    def choose(self):
        item = self.results_list.currentItem()
        if item is None:
            self.status_label.setText(
                "Сначала выберите город из списка."
            )
            return

        self.selected_location = item.data(Qt.ItemDataRole.UserRole)
        self.accept()


class WeatherMonitor(QMainWindow):
    def __init__(self, location):
        super().__init__()

        self.location = location
        self.allow_quit = False
        self.tray_available = False

        self.setWindowTitle("WeatherMonitor")
        self.resize(950, 750)

        database.initialize()
        self.setup_ui()
        self.setup_tray()

        # Фоновый сборщик погоды
        self.worker = WeatherWorker(self.location)
        self.worker.weather_updated.connect(self.on_weather_updated)
        self.worker.error_occurred.connect(self.on_weather_error)
        self.worker.start()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setSpacing(15)

        # Заголовок и местоположение
        header = QHBoxLayout()

        title = QLabel("WEATHER MONITOR")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()

        self.location_label = QLabel(self.location["name"])
        self.location_label.setStyleSheet(
            "font-size: 15px; font-weight: bold;"
        )
        header.addWidget(self.location_label)

        change_button = QPushButton("Сменить город")
        change_button.clicked.connect(self.change_location)
        header.addWidget(change_button)

        layout.addLayout(header)

        # Карточки показателей
        cards = QHBoxLayout()
        self.pressure_label = QLabel("-- hPa")
        self.temperature_label = QLabel("-- °C")

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

        self.status_label = QLabel("Ожидание данных...")
        layout.addWidget(self.status_label)

        # График давления
        self.pressure_plot = pg.PlotWidget(
            title="Атмосферное давление",
            axisItems={
                "bottom": DateAxisItem(orientation="bottom")
            },
        )
        self.pressure_plot.setLabel("left", "Давление", units="hPa")
        self.pressure_plot.setLabel("bottom", "Время")
        self.pressure_plot.showGrid(x=True, y=True, alpha=0.3)
        self.pressure_plot.setMinimumHeight(230)
        layout.addWidget(self.pressure_plot)

        self.pressure_curve = self.pressure_plot.plot(
            pen=pg.mkPen("#38a5e5", width=2),
            symbol="o",
            symbolSize=5,
        )

        # График температуры
        self.temperature_plot = pg.PlotWidget(
            title="Температура воздуха",
            axisItems={
                "bottom": DateAxisItem(orientation="bottom")
            },
        )
        self.temperature_plot.setLabel(
            "left", "Температура", units="°C"
        )
        self.temperature_plot.setLabel("bottom", "Время")
        self.temperature_plot.showGrid(x=True, y=True, alpha=0.3)
        self.temperature_plot.setMinimumHeight(230)
        layout.addWidget(self.temperature_plot)

        self.temperature_curve = self.temperature_plot.plot(
            pen=pg.mkPen("#e6a23c", width=2),
            symbol="o",
            symbolSize=5,
        )

    def setup_tray(self):
        self.tray_available = QSystemTrayIcon.isSystemTrayAvailable()

        if not self.tray_available:
            QMessageBox.warning(
                self,
                "Системный трей",
                "Системный трей недоступен. "
                "Приложение будет закрываться обычным образом.",
            )
            return

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(
            QApplication.style().standardIcon(
                QStyle.StandardPixmap.SP_ComputerIcon
            )
        )
        self.tray_icon.setToolTip("WeatherMonitor")

        tray_menu = QMenu(self)

        show_action = QAction("Открыть WeatherMonitor", self)
        show_action.triggered.connect(self.show_main_window)

        quit_action = QAction("Выход", self)
        quit_action.triggered.connect(self.quit_application)

        tray_menu.addAction(show_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def show_main_window(self):
        self.show()
        self.showNormal()
        self.activateWindow()

    def on_tray_activated(self, reason):
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.show_main_window()

    def quit_application(self):
        self.allow_quit = True

        if self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()

        if self.tray_available:
            self.tray_icon.hide()

        QApplication.quit()

    def change_location(self):
        dialog = LocationDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        new_location = dialog.selected_location
        if new_location is None:
            return

        # Если выбран тот же город, ничего не меняем
        if (
            new_location["latitude"] == self.location["latitude"]
            and new_location["longitude"] == self.location["longitude"]
        ):
            return

        answer = QMessageBox.question(
            self,
            "Смена местоположения",
            "При смене города вся накопленная история "
            "погоды будет удалена.\n\n"
            f"Новое местоположение: {new_location['name']}\n\n"
            "Продолжить?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        # Останавливаем прежний сборщик
        self.worker.stop()
        self.worker.wait()

        # Удаляем старую историю только после подтверждения
        database.clear_history()

        self.location = new_location
        save_location(self.location)
        self.location_label.setText(self.location["name"])

        self.pressure_curve.setData([], [])
        self.temperature_curve.setData([], [])
        self.pressure_label.setText("-- hPa")
        self.temperature_label.setText("-- °C")
        self.status_label.setText("Местоположение изменено.")

        # Запускаем сборщик для нового местоположения
        self.worker = WeatherWorker(self.location)
        self.worker.weather_updated.connect(self.on_weather_updated)
        self.worker.error_occurred.connect(self.on_weather_error)
        self.worker.start()

    def closeEvent(self, event):
        # При обычном закрытии скрываем окно и оставляем сборщик работать
        if self.tray_available and not self.allow_quit:
            self.hide()
            event.ignore()
            return

        if self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()

        event.accept()

    def on_weather_updated(self, weather):
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

    def on_weather_error(self, error):
        self.status_label.setText(
            f"Ошибка получения данных: {error}"
        )

    def update_graphs(self):
        history = database.get_history()
        if not history:
            return

        timezone = ZoneInfo(self.location["timezone"])
        now = datetime.now(timezone)
        cutoff = now - timedelta(days=1)

        timestamps = []
        pressures = []
        temperatures = []

        for timestamp, pressure, temperature in history:
            dt = datetime.fromisoformat(timestamp)
            # Open-Meteo возвращает местное время без UTC-смещения
            dt = dt.replace(tzinfo=timezone)

            if dt < cutoff:
                continue

            timestamps.append(dt.timestamp())
            pressures.append(pressure)
            temperatures.append(temperature)

        self.pressure_curve.setData(timestamps, pressures)
        self.temperature_curve.setData(timestamps, temperatures)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    database.initialize()
    location = load_location()

    # При первом запуске обязательно выбираем город
    if location is None:
        dialog = LocationDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            sys.exit(0)

        location = dialog.selected_location
        if location is None:
            sys.exit(0)

        save_location(location)

    window = WeatherMonitor(location)
    window.show()

    sys.exit(app.exec())
