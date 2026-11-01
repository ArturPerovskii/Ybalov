
import sys
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
    QMessageBox,
    QMenu,
    QSystemTrayIcon,
    QStyle,
)

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction

import pyqtgraph as pg
from pyqtgraph.graphicsItems.DateAxisItem import DateAxisItem

import database
from cloud_sync_worker import CloudSyncWorker


# Настройки облачного местоположения
CITY = "Lognes"
TIMEZONE = ZoneInfo("Europe/Paris")


class WeatherMonitor(QMainWindow):

    def __init__(self):
        super().__init__()

        self.allow_quit = False
        self.tray_available = False

        self.setWindowTitle("WeatherMonitor")
        self.resize(950, 750)

        database.initialize()

        self.setup_ui()
        self.setup_tray()

        # Облачная синхронизация каждые 5 минут
        self.worker = CloudSyncWorker(interval=5 * 60)

        self.worker.sync_completed.connect(
            self.on_cloud_sync_completed
        )

        self.worker.error_occurred.connect(
            self.on_cloud_sync_error
        )

        self.status_label.setText(
            "Подключение к облачной базе..."
        )

        self.worker.start()

    def setup_ui(self):

        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setSpacing(15)

        # Заголовок
        header = QHBoxLayout()

        title = QLabel("WEATHER MONITOR")
        title.setStyleSheet(
            "font-size: 24px; font-weight: bold;"
        )

        header.addWidget(title)
        header.addStretch()

        self.location_label = QLabel(CITY)
        self.location_label.setStyleSheet(
            "font-size: 15px; font-weight: bold;"
        )

        header.addWidget(self.location_label)

        self.change_button = QPushButton("Сменить город")
        self.change_button.setEnabled(False)
        self.change_button.setToolTip(
            "Пока сервер собирает данные только для Lognes"
        )

        header.addWidget(self.change_button)

        layout.addLayout(header)

        # Карточки показателей
        cards = QHBoxLayout()

        self.pressure_label = QLabel("-- hPa")
        self.temperature_label = QLabel("-- °C")

        for label in (
            self.pressure_label,
            self.temperature_label
        ):
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

        # Статус подключения
        self.status_label = QLabel(
            "Ожидание данных..."
        )

        layout.addWidget(self.status_label)

        # График давления
        self.pressure_plot = pg.PlotWidget(
            title="Атмосферное давление",
            axisItems={
                "bottom": DateAxisItem(
                    orientation="bottom"
                )
            },
        )

        self.pressure_plot.setLabel(
            "left", "Давление", units="hPa"
        )

        self.pressure_plot.setLabel(
            "bottom", "Время"
        )

        self.pressure_plot.showGrid(
            x=True, y=True, alpha=0.3
        )

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
                "bottom": DateAxisItem(
                    orientation="bottom"
                )
            },
        )

        self.temperature_plot.setLabel(
            "left", "Температура", units="°C"
        )

        self.temperature_plot.setLabel(
            "bottom", "Время"
        )

        self.temperature_plot.showGrid(
            x=True, y=True, alpha=0.3
        )

        self.temperature_plot.setMinimumHeight(230)

        layout.addWidget(self.temperature_plot)

        self.temperature_curve = (
            self.temperature_plot.plot(
                pen=pg.mkPen("#e6a23c", width=2),
                symbol="o",
                symbolSize=5,
            )
        )

    def setup_tray(self):

        self.tray_available = (
            QSystemTrayIcon.isSystemTrayAvailable()
        )

        if not self.tray_available:
            QMessageBox.warning(
                self,
                "Системный трей",
                "Системный трей недоступен. "
                "Приложение будет закрываться "
                "обычным образом.",
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

        show_action = QAction(
            "Открыть WeatherMonitor", self
        )

        show_action.triggered.connect(
            self.show_main_window
        )

        quit_action = QAction("Выход", self)

        quit_action.triggered.connect(
            self.quit_application
        )

        tray_menu.addAction(show_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)

        self.tray_icon.activated.connect(
            self.on_tray_activated
        )

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

    def stop_worker(self):

        if self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()

    def quit_application(self):

        self.allow_quit = True

        self.stop_worker()

        if self.tray_available:
            self.tray_icon.hide()

        QApplication.quit()

    def closeEvent(self, event):

        # При обычном закрытии скрываем окно в трей
        if self.tray_available and not self.allow_quit:
            self.hide()
            event.ignore()
            return

        self.stop_worker()

        event.accept()

    def on_cloud_sync_completed(self, result):

        latest = result["latest"]

        if latest is not None:

            self.pressure_label.setText(
                f'{latest["pressure"]:.1f} hPa'
            )

            self.temperature_label.setText(
                f'{latest["temperature"]:.1f} °C'
            )

            timestamp = datetime.fromisoformat(
                latest["timestamp"].replace(
                    "Z", "+00:00"
                )
            )

            timestamp = timestamp.astimezone(TIMEZONE)

            self.status_label.setText(
                "Последнее измерение: "
                + timestamp.strftime("%d.%m.%Y %H:%M:%S")
                + f' | Загружено записей: {result["count"]}'
            )

        else:

            self.status_label.setText(
                "Облачная база пока пуста."
            )

        self.update_graphs()

    def on_cloud_sync_error(self, error):

        self.status_label.setText(
            f"Ошибка синхронизации: {error}"
        )

    def update_graphs(self):

        history = database.get_history()

        if not history:
            return

        now = datetime.now(TIMEZONE)
        cutoff = now - timedelta(days=1)

        timestamps = []
        pressures = []
        temperatures = []

        for timestamp, pressure, temperature in history:

            dt = datetime.fromisoformat(
                timestamp.replace("Z", "+00:00")
            )

            # Старые локальные записи могли быть
            # сохранены без часового пояса.
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=TIMEZONE)
            else:
                dt = dt.astimezone(TIMEZONE)

            if dt < cutoff:
                continue

            timestamps.append(dt.timestamp())
            pressures.append(pressure)
            temperatures.append(temperature)

        self.pressure_curve.setData(
            timestamps, pressures
        )

        self.temperature_curve.setData(
            timestamps, temperatures
        )


if __name__ == "__main__":

    app = QApplication(sys.argv)

    app.setQuitOnLastWindowClosed(False)

    database.initialize()

    window = WeatherMonitor()
    window.show()

    sys.exit(app.exec())
