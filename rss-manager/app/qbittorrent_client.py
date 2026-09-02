from __future__ import annotations

import json
from typing import Any

import httpx


class QbittorrentError(Exception):
    """qBittorrent 回傳非預期狀態碼。"""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"{status_code}: {detail}")


class QbittorrentTimeoutError(Exception):
    """呼叫 qBittorrent API 逾時。"""


class QbittorrentClient:
    def __init__(self, base_url: str, timeout: float = 15.0) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            resp = await self._client.request(method, path, **kwargs)
        except httpx.TimeoutException as exc:
            raise QbittorrentTimeoutError(f"{method} {path} 逾時") from exc
        if resp.status_code >= 400:
            raise QbittorrentError(resp.status_code, resp.text)
        return resp

    async def get_items(self) -> dict[str, Any]:
        resp = await self._request("GET", "/rss/items", params={"withData": "false"})
        return resp.json()

    async def feed_url_exists(self, feed_url: str) -> bool:
        items = await self.get_items()

        def walk(node: Any) -> bool:
            if isinstance(node, dict):
                if node.get("url") == feed_url:
                    return True
                return any(walk(v) for v in node.values())
            return False

        return walk(items)

    async def add_feed(self, feed_url: str, path: str) -> None:
        await self._request("POST", "/rss/addFeed", data={"url": feed_url, "path": path})

    async def create_category(self, category: str, save_path: str) -> None:
        try:
            await self._request(
                "POST", "/torrents/createCategory", data={"category": category, "savePath": save_path}
            )
        except QbittorrentError as exc:
            if exc.status_code != 409:  # 409 = 分類已存在,視為正常(重新輸入同一部劇)
                raise

    async def set_rule(self, rule_name: str, rule_def: dict[str, Any]) -> None:
        await self._request(
            "POST",
            "/rss/setRule",
            data={"ruleName": rule_name, "ruleDef": json.dumps(rule_def, ensure_ascii=False)},
        )

    async def refresh_item(self, item_path: str) -> None:
        await self._request("POST", "/rss/refreshItem", data={"itemPath": item_path})

    async def matching_articles(self, rule_name: str) -> dict[str, list[str]]:
        resp = await self._request("GET", "/rss/matchingArticles", params={"ruleName": rule_name})
        return resp.json()
