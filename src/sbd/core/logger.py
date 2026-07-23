"""Unified logging setup.

Called once from main.py before any module logs anything.
"""

from __future__ import annotations

import logging

from sbd.core.config import Settings


def setup_logging(settings: Settings) -> None:
    logging.basicConfig(
        level=settings.logging.level,
        format=settings.logging.format,
    )
