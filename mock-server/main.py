import uvicorn
import sys

from config import HOST, PORT, LOG_LEVEL


def run():
    # Disable reload on Windows due to multiprocessing issues
    reload = "win" not in sys.platform.lower()

    uvicorn.run(
        "app:app",
        host=HOST,
        port=PORT,
        log_level=LOG_LEVEL,
        reload=reload,
    )


if __name__ == "__main__":
    run()
