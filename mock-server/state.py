from __future__ import annotations
from collections import deque

from models.scenario import Scenario

routes_cache: dict[tuple[str, str], list[Scenario]] = {}
request_logs: deque = deque(maxlen=100)
server_running: bool = False
