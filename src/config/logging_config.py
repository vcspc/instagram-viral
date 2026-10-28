"""Configuração de logging com suporte UTF-8."""
import logging
import sys


def setup_logging(level: int = logging.INFO) -> None:
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Reduz ruído de logs de terceiros
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("instagrapi").setLevel(logging.WARNING)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    if not root_logger.handlers:
        root_logger.addHandler(handler)
