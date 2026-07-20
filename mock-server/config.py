from pathlib import Path

API_DIR: Path = Path(__file__).parent / "api"
API_DIR.mkdir(parents=True, exist_ok=True)

HOST: str = "0.0.0.0"
PORT: int = 8000
LOG_LEVEL: str = "info"
