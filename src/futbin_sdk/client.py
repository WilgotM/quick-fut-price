"""FUTBIN API Client

Supports EA FC 27 (default), FC 26 and older years via the ``year`` parameter.
Player prices are read from FUTBIN's year-scoped player pages
(e.g. ``/27/player/<id>/...``) since the legacy ``futbin.org`` JSON API
was shut down.
"""

import asyncio
import concurrent.futures
import re
from typing import Any, cast

import httpx
from bs4 import BeautifulSoup
from cachetools import TTLCache  # type: ignore[import-untyped]
from fake_useragent import UserAgent
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from futbin_sdk.models import (
    CardVersionInfo,
    ChemistryStyle,
    FullPlayer,
    League,
    ManagerCard,
    Platform,
    PlayerPrice,
    PlayerSearchOptions,
    PopularPlayer,
)

# API Base URLs
# NOTE: FUTBIN_API_BASE (futbin.org) is legacy and currently returns 404 for
# every endpoint. It is kept for backwards compatibility only.
FUTBIN_API_BASE = "https://www.futbin.org/futbin/api"
FUTBIN_WEB_BASE = "https://www.futbin.com"

# Supported game years. 27 == EA FC 27 (current default).
DEFAULT_YEAR = 27
SUPPORTED_YEARS = (27, 26, 25, 24)

# Year-scoped web endpoints (verified live 2026-09-20)
SEARCH_PATH = "players/search"
PLAYER_PAGE_TEMPLATE = "{year}/player/{player_id}/player"
PLAYERS_LIST_TEMPLATE = "{year}/players"
LATEST_TEMPLATE = "{year}/latest"
POPULAR_PATH = "popular"

# 默认配置
DEFAULT_TIMEOUT = 30
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_DELAY = 2
DEFAULT_CACHE_TTL = 180  # 3 分钟缓存
DEFAULT_CACHE_MAXSIZE = 1000

# User Agent 生成器
_ua = UserAgent()



def _get_default_headers() -> dict[str, str]:
    """获取默认请求头（随机 User-Agent）"""
    return {
        "User-Agent": _ua.random,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.futbin.com/",
        "Origin": "https://www.futbin.com",
    }


class FutbinError(Exception):
    """FUTBIN API 错误"""

    pass


def _run_sync(client: "FutbinClient", coro_func: Any, *args: Any, **kwargs: Any) -> Any:
    """同步运行协程（为每次调用重置 async_client）

    Args:
        client: FutbinClient 实例
        coro_func: 返回协程的可调用对象
        *args, **kwargs: 传递给 coro_func 的参数
    """
    # 重置 async_client 避免 event loop 问题
    if client._async_client is not None:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # 不在运行的 loop 中，需要重置 client
            client._async_client = None

    async def run_with_cleanup() -> Any:
        try:
            return await coro_func(*args, **kwargs)
        finally:
            # 确保关闭 client
            if client._async_client is not None:
                await client._async_client.aclose()
                client._async_client = None

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, run_with_cleanup())
            return future.result()
    return asyncio.run(run_with_cleanup())


class FutbinClient:
    """FUTBIN API 客户端

    支持同步和异步调用方式，内置 TTL 缓存。

    Usage:
        # 异步使用
        async with FutbinClient() as client:
            price = await client.get_player_price(12345, Platform.PS)

        # 同步使用
        client = FutbinClient()
        price = client.get_player_price_sync(12345, Platform.PS)
    """

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        proxy: str | None = None,
        headers: dict[str, str] | None = None,
        cache_ttl: int = DEFAULT_CACHE_TTL,
        cache_maxsize: int = DEFAULT_CACHE_MAXSIZE,
        enable_cache: bool = True,
        year: int = DEFAULT_YEAR,
    ):
        self.timeout = timeout
        self.proxy = proxy
        self._custom_headers = headers or {}
        self._async_client: httpx.AsyncClient | None = None
        self._sync_client: httpx.Client | None = None
        self._enable_cache = enable_cache
        self._cache: TTLCache[str, Any] = TTLCache(maxsize=cache_maxsize, ttl=cache_ttl)
        self.year = self._resolve_year(year)

    @staticmethod
    def _resolve_year(year: int | None, fallback: int = DEFAULT_YEAR) -> int:
        """Validate/normalise a game year (e.g. 27 for EA FC 27)."""
        resolved = fallback if year is None else int(year)
        if resolved not in SUPPORTED_YEARS:
            raise FutbinError(
                f"Unsupported year {resolved!r}. Supported years: {list(SUPPORTED_YEARS)}. "
                "FC 27 is the current default."
            )
        return resolved

    def _get_headers(self) -> dict[str, str]:
        """获取请求头（每次调用生成新的随机 UA）"""
        return {**_get_default_headers(), **self._custom_headers}

    async def __aenter__(self) -> "FutbinClient":
        self._async_client = httpx.AsyncClient(
            timeout=self.timeout,
            proxy=self.proxy,
            headers=self._get_headers(),
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._async_client:
            await self._async_client.aclose()
            self._async_client = None

    def __enter__(self) -> "FutbinClient":
        self._sync_client = httpx.Client(
            timeout=self.timeout,
            proxy=self.proxy,
            headers=self._get_headers(),
        )
        return self

    def __exit__(self, *args: Any) -> None:
        if self._sync_client:
            self._sync_client.close()
            self._sync_client = None

    @property
    def async_client(self) -> httpx.AsyncClient:
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                timeout=self.timeout,
                proxy=self.proxy,
                headers=self._get_headers(),
            )
        return self._async_client

    @property
    def sync_client(self) -> httpx.Client:
        if self._sync_client is None:
            self._sync_client = httpx.Client(
                timeout=self.timeout,
                proxy=self.proxy,
                headers=self._get_headers(),
            )
        return self._sync_client

    def _get_cache_key(self, method: str, *args: Any, **kwargs: Any) -> str:
        """生成缓存键"""
        key_parts = [method, *[str(a) for a in args], *[f"{k}={v}" for k, v in sorted(kwargs.items())]]
        return ":".join(key_parts)

    def _get_from_cache(self, key: str) -> Any:
        """从缓存获取"""
        if not self._enable_cache:
            return None
        return self._cache.get(key)

    def _set_to_cache(self, key: str, value: Any) -> None:
        """设置缓存"""
        if self._enable_cache:
            self._cache[key] = value

    def clear_cache(self) -> None:
        """清空缓存"""
        self._cache.clear()

    # =========================================================================
    # 内部请求方法
    # =========================================================================

    @retry(
        stop=stop_after_attempt(DEFAULT_RETRY_ATTEMPTS),
        wait=wait_fixed(DEFAULT_RETRY_DELAY),
        retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException)),
    )
    async def _api_get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """发送 API GET 请求"""
        url = f"{FUTBIN_API_BASE}/{endpoint}"
        resp = await self.async_client.get(url, params=params)
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result

    @retry(
        stop=stop_after_attempt(DEFAULT_RETRY_ATTEMPTS),
        wait=wait_fixed(DEFAULT_RETRY_DELAY),
        retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException)),
    )
    async def _web_get(self, path: str, params: dict[str, Any] | None = None) -> str:
        """发送网页 GET 请求"""
        url = f"{FUTBIN_WEB_BASE}/{path}"
        resp = await self.async_client.get(url, params=params)
        resp.raise_for_status()
        return resp.text

    # =========================================================================
    # FC27 helpers (year-scoped web endpoints)
    # =========================================================================

    async def _search_json(self, query: str, year: int) -> list[dict[str, Any]]:
        """Name search via /players/search?year=<yy> (JSON)."""
        url = f"{FUTBIN_WEB_BASE}/{SEARCH_PATH}"
        params = {
            "targetPage": "PLAYER_PAGE",
            "query": query,
            "year": str(year),
            "evolutions": "false",
        }
        resp = await self.async_client.get(url, params=params)
        resp.raise_for_status()
        data: list[dict[str, Any]] = resp.json()
        return data

    async def _player_page_html(self, player_id: int | str, year: int) -> str:
        """Fetch a year-scoped player page (placeholder slug works)."""
        path = PLAYER_PAGE_TEMPLATE.format(year=year, player_id=player_id)
        try:
            return await self._web_get(path)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise FutbinError(f"Player {player_id} not found for FC {year}") from exc
            raise

    @staticmethod
    def _resource_id_from_image(item: dict[str, Any]) -> int:
        """EA resource id is embedded in the player image URL (.../players/<id>.png)."""
        try:
            url: str = item["playerImage"]["fixed"]["url"]["image1x"]
        except (KeyError, TypeError):
            return 0
        match = re.search(r"/players/(\d+)\.png", url)
        return int(match.group(1)) if match else 0

    @staticmethod
    def _text_of_location_url(item: dict[str, Any]) -> str:
        try:
            return str(item["location"]["url"])
        except (KeyError, TypeError):
            return ""

    def _search_item_to_player(self, item: dict[str, Any], year: int) -> FullPlayer:
        """Convert a /players/search JSON hit to a FullPlayer (basic fields)."""
        rating_raw = item.get("ratingSquare", {}).get("rating", 0)
        try:
            rating = int(rating_raw)
        except (TypeError, ValueError):
            rating = 0
        return FullPlayer(
            futbin_id=int(item.get("id", 0)),
            resource_id=self._resource_id_from_image(item),
            name=str(item.get("name", "")),
            rating=rating,
            position=str(item.get("position", "")),
        )

    def _parse_price_box(self, html: str, platform: Platform) -> PlayerPrice:
        """Parse current PS/PC price from a year-scoped player page.

        Primary selector: ``.price-box.platform-{ps,pc}-only ... .lowest-price-1``.
        Fallback: the review sentence
        "His current price on FUT is X on PlayStation, Y on Xbox, and Z on PC."
        """
        soup = BeautifulSoup(html, "html.parser")
        box_class = "platform-ps-only" if platform in (Platform.PS, Platform.XBOX) else "platform-pc-only"
        box = soup.select_one(f".price-box.{box_class}")
        if box is not None:
            lowest = box.select_one("[class*='lowest-price']")
            if lowest is not None:
                price = self._parse_price_text(lowest.get_text(" ", strip=True))
                if price > 0:
                    others = [
                        self._parse_price_text(el.get_text(" ", strip=True))
                        for el in box.select("[class*='lowest-price']")
                    ]
                    others = [p for p in others if p > 0]
                    return PlayerPrice(
                        price=price,
                        min_price=min(others) if others else 0,
                        max_price=max(others) if others else 0,
                    )
        # Fallback: review sentence with all three platform prices.
        text = soup.get_text(" ", strip=True)
        match = re.search(
            r"current price on FUT is ([\d,]+) on PlayStation, ([\d,]+) on Xbox, and ([\d,]+) on PC",
            text,
        )
        if match:
            ps = int(match.group(1).replace(",", ""))
            pc = int(match.group(3).replace(",", ""))
            price = ps if platform in (Platform.PS, Platform.XBOX) else pc
            return PlayerPrice(price=price)
        return PlayerPrice(price=0)

    @staticmethod
    def _player_id_from_url(url: str) -> int:
        match = re.search(r"/player/(\d+)/", url)
        return int(match.group(1)) if match else 0

    @staticmethod
    def _name_from_slug(url: str) -> str:
        slug = url.rstrip("/").rsplit("/", 1)[-1]
        return slug.replace("-", " ").title() if slug and slug != "player" else ""

    def _parse_players_table(self, html: str) -> list[FullPlayer]:
        """Parse the ``/{year}/players`` ranking table (30 rows/page)."""
        soup = BeautifulSoup(html, "html.parser")
        players: list[FullPlayer] = []
        for row in soup.select("tr.player-row"):
            link = row.select_one("a[href*='/player/']")
            if link is None:
                continue
            url = str(link.get("href", ""))
            futbin_id = self._player_id_from_url(url)
            if not futbin_id:
                continue
            cells = row.find_all("td")
            texts = [c.get_text(" ", strip=True) for c in cells]
            # Columns: Name | RAT | IS | POS | PS price | PC price | ... | PAC SHO PAS DRI DEF PHY | ...
            rating = self._num(texts[1]) if len(texts) > 1 else 0
            position = texts[3].split()[0] if len(texts) > 3 else ""
            price_ps = self._parse_price_text(texts[4]) if len(texts) > 4 else 0
            price_pc = self._parse_price_text(texts[5]) if len(texts) > 5 else 0
            stats = [self._num(t) for t in texts[10:16]] + [0] * 6
            players.append(
                FullPlayer(
                    futbin_id=futbin_id,
                    name=self._name_from_slug(url),
                    rating=rating,
                    position=position,
                    price_ps=price_ps,
                    price_pc=price_pc,
                    pace=stats[0],
                    shooting=stats[1],
                    passing=stats[2],
                    dribbling=stats[3],
                    defending=stats[4],
                    physical=stats[5],
                )
            )
        return players

    @staticmethod
    def _num(text: str) -> int:
        try:
            return int(float(text.replace(",", "").strip() or 0))
        except (ValueError, AttributeError):
            return 0

    # =========================================================================
    # Player Price APIs
    # =========================================================================

    async def get_player_price(
        self,
        player_id: int | str,
        platform: Platform = Platform.PS,
        year: int | None = None,
    ) -> PlayerPrice:
        """Get player price by FUTBIN ID (FC 27 by default).

        Reads the year-scoped player page (``/{year}/player/<id>/...``).

        Args:
            player_id: FUTBIN player ID
            platform: platform (PS/PC/XB, Xbox shares the PS market)
            year: game year, e.g. 27 for FC 27 (defaults to client year)

        Returns:
            PlayerPrice object
        """
        resolved_year = self._resolve_year(year, self.year)
        cache_key = self._get_cache_key("get_player_price", player_id, platform.value, resolved_year)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cast(PlayerPrice, cached)

        html = await self._player_page_html(player_id, resolved_year)
        result = self._parse_price_box(html, platform)

        self._set_to_cache(cache_key, result)
        return result

    def get_player_price_sync(
        self,
        player_id: int | str,
        platform: Platform = Platform.PS,
        year: int | None = None,
    ) -> PlayerPrice:
        """同步获取球员价格"""
        return cast(PlayerPrice, _run_sync(self, self.get_player_price, player_id, platform, year))

    async def get_player_price_by_resource_id(
        self,
        resource_id: int | str,
        platform: Platform = Platform.PS,
        year: int | None = None,
    ) -> PlayerPrice:
        """Get player price by EA Resource ID (resolved via name search).

        Args:
            resource_id: EA Resource ID (embedded in FUTBIN player images)
            platform: platform
            year: game year, e.g. 27 for FC 27 (defaults to client year)

        Returns:
            PlayerPrice 对象
        """
        resolved_year = self._resolve_year(year, self.year)
        cache_key = self._get_cache_key(
            "get_player_price_by_resource_id", resource_id, platform.value, resolved_year
        )
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cast(PlayerPrice, cached)

        hits = await self._search_json(str(resource_id), resolved_year)
        futbin_id: int | None = None
        for hit in hits:
            if self._resource_id_from_image(hit) == int(resource_id):
                futbin_id = int(hit.get("id", 0))
                break
        if futbin_id is None:
            raise FutbinError(
                f"No FC {resolved_year} player for resource id {resource_id}. "
                "Tip: search_players(query=<name>) returns the EA resource id "
                "for each hit, then call get_player_price(futbin_id)."
            )
        result = await self.get_player_price(futbin_id, platform, resolved_year)

        self._set_to_cache(cache_key, result)
        return result

    def get_player_price_by_resource_id_sync(
        self,
        resource_id: int | str,
        platform: Platform = Platform.PS,
        year: int | None = None,
    ) -> PlayerPrice:
        """同步通过 EA Resource ID 获取球员价格"""
        return cast(
            PlayerPrice, _run_sync(self, self.get_player_price_by_resource_id, resource_id, platform, year)
        )

    async def get_players_prices(
        self,
        player_ids: list[int | str],
        platform: Platform = Platform.PS,
        year: int | None = None,
    ) -> dict[str, PlayerPrice]:
        """批量获取球员价格 (one player page per id, fetched concurrently)

        Args:
            player_ids: FUTBIN 球员 ID 列表
            platform: 游戏平台
            year: game year, e.g. 27 for FC 27 (defaults to client year)

        Returns:
            {player_id: PlayerPrice} 字典
        """
        resolved_year = self._resolve_year(year, self.year)
        semaphore = asyncio.Semaphore(5)

        async def fetch(pid: int | str) -> tuple[str, PlayerPrice]:
            async with semaphore:
                return str(pid), await self.get_player_price(pid, platform, resolved_year)

        pairs = await asyncio.gather(*[fetch(pid) for pid in player_ids])
        return dict(pairs)

    def get_players_prices_sync(
        self,
        player_ids: list[int | str],
        platform: Platform = Platform.PS,
        year: int | None = None,
    ) -> dict[str, PlayerPrice]:
        """同步批量获取球员价格"""
        return cast(
            dict[str, PlayerPrice], _run_sync(self, self.get_players_prices, player_ids, platform, year)
        )

    async def get_players_prices_concurrent(
        self,
        player_ids: list[int | str],
        platform: Platform = Platform.PS,
        batch_size: int = 50,
        max_concurrency: int = 5,
        year: int | None = None,
    ) -> dict[str, PlayerPrice]:
        """并发批量获取球员价格（大量球员时使用）

        Args:
            player_ids: FUTBIN 球员 ID 列表
            platform: 游戏平台
            batch_size: 每批大小
            max_concurrency: 最大并发数
            year: game year, e.g. 27 for FC 27 (defaults to client year)

        Returns:
            {player_id: PlayerPrice} 字典
        """
        resolved_year = self._resolve_year(year, self.year)
        semaphore = asyncio.Semaphore(max_concurrency)
        batches = [player_ids[i : i + batch_size] for i in range(0, len(player_ids), batch_size)]

        async def fetch_batch(batch: list[int | str]) -> dict[str, PlayerPrice]:
            async with semaphore:
                return await self.get_players_prices(batch, platform, resolved_year)

        results = await asyncio.gather(*[fetch_batch(batch) for batch in batches])
        merged: dict[str, PlayerPrice] = {}
        for batch_result in results:
            merged.update(batch_result)
        return merged

    # =========================================================================
    # Popular Players API
    # =========================================================================

    async def get_popular_players(
        self, year: int | None = None, limit: int = 25
    ) -> list[PopularPlayer]:
        """Get trending players from /popular (FC 27 by default).

        Args:
            year: game year, e.g. 27 for FC 27 (defaults to client year)
            limit: max players to return

        Returns:
            PopularPlayer 列表
        """
        resolved_year = self._resolve_year(year, self.year)
        cache_key = self._get_cache_key("get_popular_players", resolved_year, limit)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cast(list[PopularPlayer], cached)

        html = await self._web_get(POPULAR_PATH)
        soup = BeautifulSoup(html, "html.parser")
        players: list[PopularPlayer] = []
        seen: set[int] = set()
        prefix = f"/{resolved_year}/player/"
        for anchor in soup.select("a.playercard-wrapper[href]"):
            url = str(anchor.get("href", ""))
            if not url.startswith(prefix):
                continue
            futbin_id = self._player_id_from_url(url)
            if not futbin_id or futbin_id in seen:
                continue
            seen.add(futbin_id)
            ps_el = anchor.select_one(".platform-ps-only .price-segment")
            pc_el = anchor.select_one(".platform-pc-only .price-segment")
            rating = 0
            rating_el = anchor.select_one("[class*='rating']")
            if rating_el is not None:
                rating = self._num(rating_el.get_text(" ", strip=True).split()[0])
            players.append(
                PopularPlayer(
                    futbin_id=futbin_id,
                    name=self._name_from_slug(url),
                    rating=rating,
                    price_ps=self._parse_price_text(ps_el.get_text(" ", strip=True)) if ps_el else 0,
                    price_pc=self._parse_price_text(pc_el.get_text(" ", strip=True)) if pc_el else 0,
                )
            )
            if len(players) >= limit:
                break

        self._set_to_cache(cache_key, players)
        return players

    def get_popular_players_sync(
        self, year: int | None = None, limit: int = 25
    ) -> list[PopularPlayer]:
        """同步获取热门球员列表"""
        return cast(list[PopularPlayer], _run_sync(self, self.get_popular_players, year, limit))

    # =========================================================================
    # Search / Filter Players API
    # =========================================================================

    async def search_players(
        self,
        options: PlayerSearchOptions | None = None,
        year: int | None = None,
        **kwargs: Any,
    ) -> list[FullPlayer]:
        """Search players (FC 27 by default).

        Two modes:

        1. Name search: pass ``query="Mbappe"`` (keyword arg). Uses the
           ``/players/search?year=<yy>`` JSON API and returns full basic
           info (FUTBIN id, EA resource id, name, rating, position).
        2. Browse: without ``query`` the year-scoped ``/{year}/players``
           ranking table (page 1, 30 rows) is scraped, including live
           PS/PC prices and face stats. ``PlayerSearchOptions`` filters
           ``min_rating``/``max_rating``/``position`` are applied locally.

        NOTE: the legacy server-side 40+ attribute filtering
        (``getFilteredPlayers``) was shut down with ``futbin.org`` and is
        not available. Detailed numeric filters in ``options`` other than
        rating/position are currently ignored.

        Args:
            options: 搜索选项对象
            year: game year, e.g. 27 for FC 27 (defaults to client year)
            **kwargs: ``query`` for name search, ``page`` for browse mode

        Returns:
            FullPlayer 列表
        """
        resolved_year = self._resolve_year(year if year is not None else kwargs.get("year"), self.year)
        query = kwargs.get("query") or kwargs.get("name")
        if query:
            limit = int(kwargs.get("limit", 30))
            hits = await self._search_json(str(query), resolved_year)
            return [self._search_item_to_player(h, resolved_year) for h in hits[:limit]]

        page = int(kwargs.get("page", getattr(options, "page", 1) or 1))
        html = await self._web_get(
            PLAYERS_LIST_TEMPLATE.format(year=resolved_year), {"page": page} if page > 1 else None
        )
        players = self._parse_players_table(html)
        if options is not None:
            if options.min_rating is not None:
                players = [p for p in players if p.rating >= options.min_rating]
            if options.max_rating is not None:
                players = [p for p in players if p.rating <= options.max_rating]
            if options.position:
                wanted = {pos.upper() for pos in options.position}
                players = [p for p in players if p.position.upper() in wanted]
        return players

    def search_players_sync(
        self,
        options: PlayerSearchOptions | None = None,
        **kwargs: Any,
    ) -> list[FullPlayer]:
        """同步搜索球员"""
        return cast(list[FullPlayer], _run_sync(self, self.search_players, options, **kwargs))

    async def get_totw(self, year: int | None = None) -> list[FullPlayer]:
        """Get the current Team of the Week (FC 27 by default).

        The active TOTW squad URL (``/{year}/totw/<SquadName>``) is
        discovered from the FUTBIN homepage, then its player cards are
        scraped.

        Args:
            year: game year, e.g. 27 for FC 27 (defaults to client year)

        Returns:
            FullPlayer 列表
        """
        resolved_year = self._resolve_year(year, self.year)
        cache_key = self._get_cache_key("get_totw", resolved_year)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cast(list[FullPlayer], cached)

        home = await self._web_get("")
        squad_urls = re.findall(rf'"/{resolved_year}/totw/([^"]+)"', home)
        squad = squad_urls[0] if squad_urls else "TeamOfTheWeek1"
        squad_html = await self._web_get(f"{resolved_year}/totw/{squad}")

        soup = BeautifulSoup(squad_html, "html.parser")
        players: list[FullPlayer] = []
        seen: set[int] = set()
        prefix = f"/{resolved_year}/player/"
        for anchor in soup.select("a[href]"):
            url = str(anchor.get("href", ""))
            if not url.startswith(prefix):
                continue
            futbin_id = self._player_id_from_url(url)
            if not futbin_id or futbin_id in seen:
                continue
            seen.add(futbin_id)
            players.append(
                FullPlayer(futbin_id=futbin_id, name=self._name_from_slug(url)),
            )

        self._set_to_cache(cache_key, players)
        return players

    def get_totw_sync(self, year: int | None = None) -> list[FullPlayer]:
        """同步获取本周最佳球员"""
        return cast(list[FullPlayer], _run_sync(self, self.get_totw, year))

    async def get_latest_players(
        self, year: int | None = None, limit: int = 30
    ) -> list[FullPlayer]:
        """Get newly added players from /{year}/latest (FC 27 by default).

        The table includes live Cross (PS/Xbox) and PC prices.

        Args:
            year: game year, e.g. 27 for FC 27 (defaults to client year)
            limit: max players to return

        Returns:
            FullPlayer 列表
        """
        resolved_year = self._resolve_year(year, self.year)
        cache_key = self._get_cache_key("get_latest_players", resolved_year, limit)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cast(list[FullPlayer], cached)

        html = await self._web_get(LATEST_TEMPLATE.format(year=resolved_year))
        soup = BeautifulSoup(html, "html.parser")
        players: list[FullPlayer] = []
        for row in soup.select("tr"):
            link = row.select_one("a[href*='/player/']")
            if link is None:
                continue
            url = str(link.get("href", ""))
            if not url.startswith(f"/{resolved_year}/player/"):
                continue
            futbin_id = self._player_id_from_url(url)
            if not futbin_id:
                continue
            cells = [c.get_text(" ", strip=True) for c in row.find_all("td")]
            # Columns: Name | Rating | Position | Cross Price | ... | PC Price | ... | Added on
            players.append(
                FullPlayer(
                    futbin_id=futbin_id,
                    name=self._name_from_slug(url),
                    rating=self._num(cells[1]) if len(cells) > 1 else 0,
                    position=cells[2].split()[0] if len(cells) > 2 else "",
                    price_ps=self._parse_price_text(cells[3]) if len(cells) > 3 else 0,
                    price_pc=self._parse_price_text(cells[5]) if len(cells) > 5 else 0,
                )
            )
            if len(players) >= limit:
                break

        self._set_to_cache(cache_key, players)
        return players

    def get_latest_players_sync(
        self, year: int | None = None, limit: int = 30
    ) -> list[FullPlayer]:
        """同步获取最新球员"""
        return cast(list[FullPlayer], _run_sync(self, self.get_latest_players, year, limit))

    # =========================================================================
    # Leagues & Clubs API
    # =========================================================================

    async def get_leagues_and_clubs(self) -> list[League]:
        """获取所有联赛和俱乐部

        .. deprecated::
            The backing endpoint (``getLeaguesAndClubsAndroid`` on the
            legacy ``futbin.org`` API) was shut down. This method now
            raises :class:`FutbinError`; use the year-scoped website
            (Clubs, Leagues & Nations section) instead.

        Returns:
            League 列表（每个联赛包含其俱乐部）
        """
        raise FutbinError(
            "get_leagues_and_clubs is unavailable: the legacy futbin.org endpoint "
            "returns 404. No year-scoped replacement has been verified yet."
        )

    def get_leagues_and_clubs_sync(self) -> list[League]:
        """同步获取所有联赛和俱乐部"""
        return cast(list[League], _run_sync(self, self.get_leagues_and_clubs, ))

    # =========================================================================
    # Card Versions API
    # =========================================================================

    async def get_card_versions(self) -> list[CardVersionInfo]:
        """获取所有卡片版本

        .. deprecated::
            The backing endpoint (``getCardVersions`` on the legacy
            ``futbin.org`` API) was shut down. This method now raises
            :class:`FutbinError`.

        Returns:
            CardVersionInfo 列表
        """
        raise FutbinError(
            "get_card_versions is unavailable: the legacy futbin.org endpoint "
            "returns 404. No year-scoped replacement has been verified yet."
        )

    def get_card_versions_sync(self) -> list[CardVersionInfo]:
        """同步获取所有卡片版本"""
        return cast(list[CardVersionInfo], _run_sync(self, self.get_card_versions, ))

    # =========================================================================
    # Consumables API (Web Scraping)
    # =========================================================================

    def _parse_price_text(self, text: str) -> int:
        """解析价格文本（支持 K/M 后缀）"""
        if not text:
            return 0
        text = text.strip().upper().replace(",", "")
        try:
            if text.endswith("K"):
                return int(float(text[:-1]) * 1000)
            elif text.endswith("M"):
                return int(float(text[:-1]) * 1000000)
            return int(float(text))
        except (ValueError, TypeError):
            return 0

    async def get_chemistry_styles(self, platform: Platform = Platform.PS) -> list[ChemistryStyle]:
        """获取化学卡价格列表

        Args:
            platform: 游戏平台

        Returns:
            ChemistryStyle 列表
        """
        cache_key = self._get_cache_key("get_chemistry_styles", platform.value)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cast(list[ChemistryStyle], cached)

        html = await self._web_get("consumables/Chemistry%20Styles")
        soup = BeautifulSoup(html, "html.parser")
        styles: list[ChemistryStyle] = []

        # 查找表格 (class="players-table" 或 id="consumables-table")
        table = soup.find("table", class_="players-table")
        if not table:
            table = soup.find("table", {"id": "consumables-table"})
        if not table:
            return styles

        tbody = table.find("tbody")
        rows = tbody.find_all("tr") if tbody else table.find_all("tr")[1:]

        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 9:
                continue

            name = cols[0].get_text(strip=True)
            # 表格结构: 名称, PS价格, PC价格, PS最低, PC最低, PS最高, PC最高, 加成, 位置
            ps_price = self._parse_price_text(cols[1].get_text(strip=True))
            pc_price = self._parse_price_text(cols[2].get_text(strip=True))
            min_price_ps = self._parse_price_text(cols[3].get_text(strip=True))
            min_price_pc = self._parse_price_text(cols[4].get_text(strip=True))
            max_price_ps = self._parse_price_text(cols[5].get_text(strip=True))
            max_price_pc = self._parse_price_text(cols[6].get_text(strip=True))
            boost = cols[7].get_text(strip=True) if len(cols) > 7 else ""
            position = cols[8].get_text(strip=True) if len(cols) > 8 else ""

            styles.append(
                ChemistryStyle(
                    name=name,
                    price_ps=ps_price,
                    price_pc=pc_price,
                    min_price_ps=min_price_ps,
                    min_price_pc=min_price_pc,
                    max_price_ps=max_price_ps,
                    max_price_pc=max_price_pc,
                    boost=boost,
                    preferred_positions=[position] if position else [],
                )
            )

        self._set_to_cache(cache_key, styles)
        return styles

    def get_chemistry_styles_sync(self, platform: Platform = Platform.PS) -> list[ChemistryStyle]:
        """同步获取化学卡价格列表"""
        return cast(list[ChemistryStyle], _run_sync(self, self.get_chemistry_styles, platform))

    async def get_manager_cards(self, platform: Platform = Platform.PS) -> list[ManagerCard]:
        """获取教练员卡价格列表

        Args:
            platform: 游戏平台

        Returns:
            ManagerCard 列表
        """
        cache_key = self._get_cache_key("get_manager_cards", platform.value)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cast(list[ManagerCard], cached)

        html = await self._web_get("manager-prices")
        soup = BeautifulSoup(html, "html.parser")
        managers: list[ManagerCard] = []

        # 查找表格 (class="players-table" 或 id="managers-table")
        table = soup.find("table", class_="players-table")
        if not table:
            table = soup.find("table", {"id": "managers-table"})
        if not table:
            return managers

        tbody = table.find("tbody")
        rows = tbody.find_all("tr") if tbody else table.find_all("tr")[1:]

        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 5:
                continue

            nation = cols[0].get_text(strip=True)

            # 表格结构可能是 6 列或 7 列:
            # 国家, 铜PS, 铜PC, 银PS, 银PC, 金PS, 金PC
            # 某些国家没有铜卡时可能显示 "-"
            def get_col_price(columns: list[Any], idx: int) -> int:
                if idx < len(columns):
                    text = columns[idx].get_text(strip=True)
                    if text == "-":
                        return 0
                    return self._parse_price_text(text)
                return 0

            bronze_ps = get_col_price(cols, 1)
            bronze_pc = get_col_price(cols, 2)
            silver_ps = get_col_price(cols, 3)
            silver_pc = get_col_price(cols, 4)
            gold_ps = get_col_price(cols, 5)
            gold_pc = get_col_price(cols, 6)

            managers.append(
                ManagerCard(
                    nation=nation,
                    bronze_price_ps=bronze_ps,
                    bronze_price_pc=bronze_pc,
                    silver_price_ps=silver_ps,
                    silver_price_pc=silver_pc,
                    gold_price_ps=gold_ps,
                    gold_price_pc=gold_pc,
                )
            )

        self._set_to_cache(cache_key, managers)
        return managers

    def get_manager_cards_sync(self, platform: Platform = Platform.PS) -> list[ManagerCard]:
        """同步获取教练员卡价格列表"""
        return cast(list[ManagerCard], _run_sync(self, self.get_manager_cards, platform))
