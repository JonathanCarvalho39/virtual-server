from __future__ import annotations

import logging
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger("mock-server.watcher")


class ApiWatcher(FileSystemEventHandler):
    def __init__(self, api_dir: Path, on_change):
        super().__init__()
        self.api_dir = api_dir
        self.on_change = on_change

    def on_any_event(self, event):
        if event.is_directory:
            return

        src = Path(event.src_path)
        if src.suffix == ".json" and self.api_dir in src.parents:
            logger.info(f"Alteração detectada: {src}")
            self.on_change()


class WatchdogService:
    def __init__(self, api_dir: Path, on_change):
        self.observer = None
        self.handler = ApiWatcher(api_dir, on_change)
        self.api_dir = api_dir

    def start(self):
        self.api_dir.mkdir(parents=True, exist_ok=True)

        try:
            self.observer = Observer()
            self.observer.schedule(self.handler, str(self.api_dir), recursive=True)
            self.observer.start()
            logger.info(f"Watchdog iniciado em {self.api_dir}")
        except Exception as e:
            logger.warning(f"Watchdog não iniciado: {e}")
            self.observer = None

    def stop(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()
            logger.info("Watchdog parado")
