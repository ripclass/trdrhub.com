import threading
import time

import schedule

from app.services.rulhub_client import sync_rules_from_rulhub


def start_sync_job() -> None:
    schedule.every().monday.at("03:00").do(sync_rules_from_rulhub)

    def loop() -> None:
        while True:
            schedule.run_pending()
            time.sleep(3600)

    threading.Thread(target=loop, daemon=True).start()


