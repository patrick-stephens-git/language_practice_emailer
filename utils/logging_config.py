import logging
import sys
from pathlib import Path

LOG_DIR: Path = Path(__file__).resolve().parent.parent / "logs" # anchored to the project directory, not the current working directory

def setup_logging() -> None:
    """Send INFO and above to logs/app.log and the terminal. Call once, from an entry point."""
    LOG_DIR.mkdir(exist_ok=True) # ensure that the logs directory exists
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s: %(name)s - %(levelname)s - %(message)s (Line: %(lineno)d [%(filename)s])",
        datefmt="%d/%m/%Y %H:%M:%S",
        handlers=[
            logging.FileHandler(LOG_DIR / "app.log", mode="w", encoding="utf-8"), # only the latest trigger is kept
            logging.StreamHandler(sys.stdout),
        ],
    )
    for noisy_logger in ("httpx", "httpx2"): # hide the one-line-per-request HTTP messages
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)
