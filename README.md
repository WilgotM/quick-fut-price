# quick-fut-price

Minimal FC27 player price lookup for FUT. Search a name, see the card, and get the current price without the usual clutter.

[Project page](https://wilgotm.github.io/quick-fut-price/) · [Run locally](#touchline-web-app)

## What it is

**Unofficial** Python SDK for FUTBIN API - Access EA FC player prices, statistics, and more.

> **FC 27 status (verified live 2026-09-20):** the legacy `futbin.org`
> JSON API used by v0.1.0 returns `404` for every endpoint, so the
> original SDK no longer returns prices. This fork (v0.2.0) reimplements
> prices/search/popular/latest/TOTW on top of FUTBIN's year-scoped web
> endpoints (`/27/player/...`, `/players/search?year=27`, `/27/players`,
> `/27/latest`, `/popular`). `FutbinClient` defaults to **FC 27**; pass
> `year=26` (or `FutbinClient(year=26)`) for FC 26.

Upstream: [daojiAnime/futbin-sdk](https://github.com/daojiAnime/futbin-sdk).
Inspired by [matheusfm/futbin](https://github.com/matheusfm/futbin) (Go) and [rfutbin](https://github.com/danielredondo/rfutbin) (R).

## FC 27 Quick Start

```python
import asyncio
from futbin_sdk import FutbinClient, Platform

async def main():
    async with FutbinClient() as client:  # year=27 by default
        # Price for a FC 27 player by FUTBIN ID (Haaland = 1, Mbappe = 8)
        price = await client.get_player_price(8, Platform.PS)
        print(f"Mbappe PS: {price.price:,}")

        # Name search (returns FUTBIN id + EA resource id + rating)
        hits = await client.search_players(query="Mbappe")
        print([(h.futbin_id, h.name, h.resource_id) for h in hits])

asyncio.run(main())
```

Limitations vs v0.1.0:

- Server-side 40+ attribute filtering (`getFilteredPlayers`) is gone;
  `search_players(options=...)` scrapes the `/{year}/players` table and
  applies `min_rating`/`max_rating`/`position` locally.
- `get_player_price_by_resource_id` only works if FUTBIN's search
  resolves the numeric id; otherwise use `search_players(query=name)`
  first (each hit includes the EA `resource_id`).
- `get_leagues_and_clubs` / `get_card_versions` raise `FutbinError` —
  no replacement endpoint verified yet.

## Installation

```bash
pip install futbin-sdk
```

Or with uv:

```bash
uv add futbin-sdk
```

## Quick Start

### Async Usage (Recommended)

```python
import asyncio
from futbin_sdk import FutbinClient, Platform, PlayerSearchOptions, get_nation_name

async def main():
    async with FutbinClient() as client:
        # Get popular players
        popular = await client.get_popular_players()
        for player in popular[:5]:
            print(f"{player.name}: {player.price_ps:,} coins")

        # Get player price by FUTBIN ID
        price = await client.get_player_price(12345, Platform.PS)
        print(f"Price: {price.price:,}")

        # Search players with filters
        options = PlayerSearchOptions(
            platform="PS",
            min_rating=85,
            position=["ST", "CF"],
        )
        players = await client.search_players(options=options)

        # Advanced search with detailed attributes
        options = PlayerSearchOptions(
            platform="PS",
            min_pace=90,
            min_shooting=85,
            min_skills=4,
            min_weak_foot=4,
        )
        fast_strikers = await client.search_players(options=options)

        # Get Team of the Week
        totw = await client.get_totw()

        # Get latest players
        latest = await client.get_latest_players()

        # Get all leagues and clubs
        leagues = await client.get_leagues_and_clubs()

        # Get card versions (TOTW, TOTY, Icons, etc.)
        versions = await client.get_card_versions()

        # Use nations data
        nation = get_nation_name(54)  # Returns "Ethiopia"

asyncio.run(main())
```

### Sync Usage

```python
from futbin_sdk import FutbinClient, Platform

client = FutbinClient()
price = client.get_player_price_sync(12345, Platform.PS)
print(f"Price: {price.price}")
```

## API Reference

### Player APIs

| Method | Description |
|--------|-------------|
| `get_player_price(player_id, platform)` | Get price by FUTBIN ID |
| `get_player_price_by_resource_id(resource_id, platform)` | Get price by EA Resource ID |
| `get_players_prices(player_ids, platform)` | Batch get prices |
| `get_popular_players()` | Get trending players |
| `search_players(options)` | Search with filters |
| `get_totw()` | Get Team of the Week |
| `get_latest_players()` | Get newly added players |

### Reference Data APIs

| Method | Description |
|--------|-------------|
| `get_leagues_and_clubs()` | Get all leagues with their clubs |
| `get_card_versions()` | Get all card versions (TOTW, Icons, etc.) |

### Nations Data

```python
from futbin_sdk import NATIONS, get_nation_name, get_nation_id

# Get nation name by ID
name = get_nation_name(22)  # Returns "Brazil"

# Get nation ID by name
nation_id = get_nation_id("Brazil")  # Returns 22

# Access full nations dictionary
print(NATIONS[22])  # "Brazil"
```

### Search Options

`PlayerSearchOptions` supports **40+ detailed attributes** for filtering players:

#### Basic Filters

| Parameter | Type | Description |
|-----------|------|-------------|
| `platform` | str | Platform: "PS" or "PC" |
| `page` | int | Page number (default: 1) |
| `sort` | str | Sort field |
| `order` | str | Sort order ("asc" or "desc") |
| `version` | str | Card version filter |
| `position` | list[str] | Position filter (e.g., ["ST", "CF"]) |
| `nation_id` | int | Nation ID filter |
| `league_id` | int | League ID filter |
| `club_id` | int | Club ID filter |

#### Rating & Price

| Parameter | Type | Description |
|-----------|------|-------------|
| `min_rating` / `max_rating` | int | Rating range |
| `min_price` / `max_price` | int | Price range |

#### Skills & Physical

| Parameter | Type | Description |
|-----------|------|-------------|
| `min_skills` / `max_skills` | int | Skill moves (1-5) |
| `min_weak_foot` / `max_weak_foot` | int | Weak foot (1-5) |
| `foot` | Foot | Preferred foot (LEFT/RIGHT) |
| `min_height` / `max_height` | int | Height in cm |
| `min_weight` / `max_weight` | int | Weight in kg |

#### Six Main Attributes

| Parameter | Type | Description |
|-----------|------|-------------|
| `min_pace` / `max_pace` | int | Pace |
| `min_shooting` / `max_shooting` | int | Shooting |
| `min_passing` / `max_passing` | int | Passing |
| `min_dribbling` / `max_dribbling` | int | Dribbling |
| `min_defending` / `max_defending` | int | Defending |
| `min_physical` / `max_physical` | int | Physical |

#### Detailed Pace Attributes

| Parameter | Type | Description |
|-----------|------|-------------|
| `min_acceleration` / `max_acceleration` | int | Acceleration |
| `min_sprint_speed` / `max_sprint_speed` | int | Sprint Speed |

#### Detailed Shooting Attributes

| Parameter | Type | Description |
|-----------|------|-------------|
| `min_positioning` / `max_positioning` | int | Positioning |
| `min_finishing` / `max_finishing` | int | Finishing |
| `min_shot_power` / `max_shot_power` | int | Shot Power |
| `min_long_shots` / `max_long_shots` | int | Long Shots |
| `min_volleys` / `max_volleys` | int | Volleys |
| `min_penalties` / `max_penalties` | int | Penalties |

#### Detailed Passing Attributes

| Parameter | Type | Description |
|-----------|------|-------------|
| `min_vision` / `max_vision` | int | Vision |
| `min_crossing` / `max_crossing` | int | Crossing |
| `min_free_kick` / `max_free_kick` | int | Free Kick Accuracy |
| `min_short_passing` / `max_short_passing` | int | Short Passing |
| `min_long_passing` / `max_long_passing` | int | Long Passing |
| `min_curve` / `max_curve` | int | Curve |

#### Detailed Dribbling Attributes

| Parameter | Type | Description |
|-----------|------|-------------|
| `min_agility` / `max_agility` | int | Agility |
| `min_balance` / `max_balance` | int | Balance |
| `min_reactions` / `max_reactions` | int | Reactions |
| `min_ball_control` / `max_ball_control` | int | Ball Control |
| `min_composure` / `max_composure` | int | Composure |

#### Detailed Defending Attributes

| Parameter | Type | Description |
|-----------|------|-------------|
| `min_interceptions` / `max_interceptions` | int | Interceptions |
| `min_heading_accuracy` / `max_heading_accuracy` | int | Heading Accuracy |
| `min_marking` / `max_marking` | int | Marking |
| `min_standing_tackle` / `max_standing_tackle` | int | Standing Tackle |
| `min_sliding_tackle` / `max_sliding_tackle` | int | Sliding Tackle |

#### Detailed Physical Attributes

| Parameter | Type | Description |
|-----------|------|-------------|
| `min_jumping` / `max_jumping` | int | Jumping |
| `min_stamina` / `max_stamina` | int | Stamina |
| `min_strength` / `max_strength` | int | Strength |
| `min_aggression` / `max_aggression` | int | Aggression |

#### Goalkeeper Attributes

| Parameter | Type | Description |
|-----------|------|-------------|
| `min_gk_diving` / `max_gk_diving` | int | GK Diving |
| `min_gk_handling` / `max_gk_handling` | int | GK Handling |
| `min_gk_kicking` / `max_gk_kicking` | int | GK Kicking |
| `min_gk_positioning` / `max_gk_positioning` | int | GK Positioning |
| `min_gk_reflexes` / `max_gk_reflexes` | int | GK Reflexes |

## Models

| Model | Description |
|-------|-------------|
| `PlayerPrice` | Price info (price, min_price, max_price) |
| `PopularPlayer` | Popular player with basic info |
| `FullPlayer` | Complete player info (30+ fields) |
| `League` | League with clubs list |
| `Club` | Club info |
| `CardVersionInfo` | Card version (TOTW, TOTY, etc.) |
| `Platform` | Platform enum (PS, PC, XBOX) |
| `Position` | Position enum (GK, CB, ST, etc.) |
| `Foot` | Foot enum (LEFT, RIGHT) |

## Configuration

```python
client = FutbinClient(
    timeout=30,           # Request timeout (seconds)
    proxy="http://...",   # Proxy URL
    headers={...},        # Custom headers
)
```

## Feature Comparison

| Feature | futbin-sdk (Python) | matheusfm/futbin (Go) | rfutbin (R) |
|---------|--------------------|-----------------------|-------------|
| Player prices | ✅ | ✅ | ✅ |
| Search/filter players | ✅ | ✅ | ✅ |
| 40+ search attributes | ✅ | ✅ | ❌ |
| Popular players | ✅ | ✅ | ❌ |
| TOTW players | ✅ | ✅ | ❌ |
| Latest players | ✅ | ✅ | ❌ |
| Leagues & Clubs | ✅ | ✅ | ❌ |
| Card versions | ✅ | ✅ | ❌ |
| Nations data | ✅ | ✅ | ❌ |
| Async support | ✅ | ❌ | ❌ |
| Type hints | ✅ | ✅ | ❌ |

## Disclaimer

This is an **unofficial** SDK. FUTBIN does not provide a public API, and this SDK uses reverse-engineered endpoints that may change without notice.

- Use responsibly and respect FUTBIN's terms of service
- Rate limit your requests to avoid IP bans
- Do not use for commercial purposes without permission

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Touchline web app

A lightweight Swedish FC27 price search interface, served by the Python SDK.
No frontend build or Node runtime is required.

```bash
uv sync
uv run uvicorn futbin_sdk.web:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000. On your phone, use your computer's LAN IP and
port 8000 on the same Wi-Fi. Speech recognition requires HTTPS (or localhost),
a supported browser and microphone permission; use HTTPS when hosting for phones.

- Search as you type, with a 160 ms debounce and immediate matches from previously
  retrieved players. Exact names and surnames rank first, then prefixes and rating.
- FUTBIN's FC27 autocomplete supplies portraits, clubs, ratings and card versions.
  Results are limited to what that upstream endpoint returns, not an exhaustive
  offline catalogue. Prices load separately without blocking search results.
- Console and PC markets have separate caches. Up to five upstream requests run
  concurrently; duplicate requests are coalesced and successful data is cached for
  two minutes. “Hämtat” means retrieval time, not FUTBIN's market update time.
- Missing prices are shown as unavailable, never as zero coins or invented data.
- `/` focuses search, `Alt+V` toggles speech, and `Escape` stops speech or clears.
  These shortcuts work while the page is focused. A system-wide shortcut while
  gaming requires a desktop companion or browser extension, not a regular website.
- Speech uses the browser's recognition service (Swedish or English, configurable
  with the `?` keyboard shortcut). Audio may be sent to the browser vendor's speech service.
- This app depends on FUTBIN's unofficial endpoints. It reports upstream errors
  and offers retry; it does not substitute fake/demo prices.

Validation: `uv run pytest tests/test_web.py tests/test_fc27.py`.

The minimal interface uses San Francisco through the Apple system font stack,
with system fallbacks on other platforms. Speech errors remain visible independently
of search status. Helium exposes SpeechRecognition but may return `network` because
its Google speech backend is unavailable; Chrome/Safari or a separate transcription
backend is required for speech in that case. No separate transcription backend is configured.
