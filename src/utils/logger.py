import logging
import sys
from rich.console import Console
from rich.logging import RichHandler

console = Console()

def setup_logger(name: str = "JobRadar", level: int = logging.INFO) -> logging.Logger:
    """Rich tabanlı şık ve renkli bir logger oluşturur."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(level)
        handler = RichHandler(
            console=console,
            show_time=True,
            show_path=False,
            rich_tracebacks=True,
            markup=True
        )
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

logger = setup_logger()
