from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    qbit_base: str
    media_root: str
    dmhy_rss: str
    port: int


def get_settings() -> Settings:
    return Settings(
        qbit_base=os.environ.get("QBIT_BASE", "http://qbittorrent:8080/api/v2"),
        media_root=os.environ.get("MEDIA_ROOT", "/data/05_影音"),
        dmhy_rss=os.environ.get("DMHY_RSS", "https://share.dmhy.org/topics/rss/rss.xml"),
        port=int(os.environ.get("PORT", "5090")),
    )
