from __future__ import annotations

import asyncio
import os
import urllib.parse
from collections.abc import Awaitable, Callable

from .config import Settings
from .qbittorrent_client import QbittorrentClient

FAN = chr(0x7E41)  # 繁
QIAN = chr(0x5D4C)  # 嵌

SleepFn = Callable[[float], Awaitable[None]]

POLL_ATTEMPTS = 4
POLL_INTERVAL_SECONDS = 3.0


async def create_rule(
    keyword: str,
    *,
    client: QbittorrentClient,
    settings: Settings,
    sleep: SleepFn = asyncio.sleep,
    poll_attempts: int = POLL_ATTEMPTS,
    poll_interval: float = POLL_INTERVAL_SECONDS,
) -> dict[str, object]:
    save_path = f"{settings.media_root}/{keyword}"
    feed_url = settings.dmhy_rss + "?keyword=" + urllib.parse.quote(keyword)

    if not await client.feed_url_exists(feed_url):
        await client.add_feed(feed_url, keyword)

    os.makedirs(save_path, exist_ok=True)
    await client.create_category(keyword, save_path)

    must_contain = f"(?=.*{FAN})(?=.*{QIAN})"
    rule_def = {
        "enabled": True,
        "mustContain": must_contain,
        "mustNotContain": "",
        "useRegex": True,
        "episodeFilter": "",
        "smartFilter": False,
        "previouslyMatchedEpisodes": [],
        "affectedFeeds": [feed_url],
        "ignoreDays": 0,
        "lastMatch": "",
        "addPaused": False,
        "assignedCategory": keyword,
        "savePath": save_path,
    }
    await client.set_rule(keyword, rule_def)
    await client.refresh_item(keyword)

    # RSS 抓取+規則比對是非同步的,剛送出 refreshItem 不代表馬上抓完,
    # 用短輪詢等結果穩定下來,避免回報「0 篇符合」但其實正在背景下載。
    # sleep 可注入(測試用無操作 sleep),不依賴真實時間(→ BE-088)。
    matched_titles: list[str] = []
    for _ in range(poll_attempts):
        await sleep(poll_interval)
        matches = await client.matching_articles(keyword)
        # matches 是 {feed路徑: [標題,...]},不是用規則名當 key(重用既有 feed 時 key 會是原本的 feed 路徑名)
        matched_titles = [t for titles in matches.values() for t in titles]
        if matched_titles:
            break

    return {
        "ok": True,
        "keyword": keyword,
        "save_path": save_path,
        "feed_url": feed_url,
        "matched_count": len(matched_titles),
        "matched_titles": matched_titles[:20],
    }
