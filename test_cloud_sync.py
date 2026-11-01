
import sys

from PySide6.QtCore import QCoreApplication

import database
from cloud_sync_worker import CloudSyncWorker


app = QCoreApplication(sys.argv)

database.initialize()

worker = CloudSyncWorker(interval=300)


def on_sync(data):
    print("Синхронизация успешна!")
    print("Получено записей:", data["count"])
    print("Последнее измерение:", data["latest"])

    history = database.get_history()
    print("Записей в локальной базе:", len(history))

    worker.stop()
    app.quit()


def on_error(error):
    print("Ошибка:", error)
    worker.stop()
    app.quit()


worker.sync_completed.connect(on_sync)
worker.error_occurred.connect(on_error)

worker.start()

sys.exit(app.exec())
