from __future__ import annotations

import logging
import sys


def configurar_logging(nivel: str = "INFO") -> None:
    nivel_num = getattr(logging, nivel.upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.setLevel(nivel_num)

    root = logging.getLogger()
    root.setLevel(nivel_num)
    root.handlers.clear()
    root.addHandler(handler)

    for lib in ("sqlalchemy.engine", "httpx", "httpcore", "asyncio", "watchfiles"):
        logging.getLogger(lib).setLevel(logging.WARNING)
