import uvicorn

from config import HOST, PORT, LOG_LEVEL


def run():
    uvicorn.run(
        "app:app",
        host=HOST,
        port=PORT,
        log_level=LOG_LEVEL,
        reload=True,
    )


if __name__ == "__main__":
    run()
