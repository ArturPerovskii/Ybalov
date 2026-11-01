
import threading

from PySide6.QtCore import QThread, Signal

import cloud_api
import database


class CloudSyncWorker(QThread):
    sync_completed = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, interval=5 * 60):
        super().__init__()

        self.interval = interval
        self.stop_event = threading.Event()

    def run(self):
        print("Cloud sync worker started")

        while not self.stop_event.is_set():
            try:
                # Загружаем историю с Cloudflare
                records = cloud_api.get_history(limit=10000)

                # Сохраняем её в локальную SQLite
                database.save_weather_batch(records)

                latest = records[-1] if records else None

                self.sync_completed.emit({
                    "count": len(records),
                    "latest": latest
                })

                print(
                    f"Cloud sync completed: {len(records)} records"
                )

            except Exception as error:
                self.error_occurred.emit(str(error))
                print("Cloud sync error:", error)

            self.stop_event.wait(self.interval)

        print("Cloud sync worker stopped")

    def stop(self):
        self.stop_event.set()
