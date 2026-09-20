"""FUTBIN SDK - Python client for FUTBIN API

Unofficial SDK for accessing FIFA Ultimate Team player prices and statistics from FUTBIN.
"""

from futbin_sdk.client import DEFAULT_YEAR, SUPPORTED_YEARS, FutbinClient, FutbinError
from futbin_sdk.models import (
    CardVersion,
    CardVersionInfo,
    Club,
    Foot,
    FullPlayer,
    League,
    Platform,
    Player,
    PlayerPrice,
    PlayerSearchOptions,
    PopularPlayer,
    Position,
)
from futbin_sdk.nations import NATIONS, get_nation_id, get_nation_name

__version__ = "0.2.0"
__all__ = [
    "FutbinClient",
    "FutbinError",
    "DEFAULT_YEAR",
    "SUPPORTED_YEARS",
    # Models
    "Player",
    "PlayerPrice",
    "Platform",
    "CardVersion",
    "CardVersionInfo",
    "Club",
    "Foot",
    "FullPlayer",
    "League",
    "PlayerSearchOptions",
    "PopularPlayer",
    "Position",
    # Nations
    "NATIONS",
    "get_nation_id",
    "get_nation_name",
]
