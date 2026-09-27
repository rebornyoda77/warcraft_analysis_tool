"""Swappable data source interfaces for character gear/stats and item icons.

Today, gear/stats come from a pasted SimC addon string and icons come
from scraping Wowhead + caching from its zamimg CDN, because Blizzard's
official Game Data API is blocked behind developer-portal phone/SMS
verification. Both of those are implementations of a small interface
here (CharacterDataSource, IconSource) so that once Blizzard API access
unblocks, adding BlizzardAPIDataSource/BlizzardMediaIconSource is a new
class + a config value, not a rewrite of characters.py or icons.py.

Note on Blizzard API auth (corrected from an earlier assumption): the
per-character Profile endpoints this needs -- equipment, stats,
character-media -- only need the OAuth2 client-credentials flow (a
single app-scoped token via POST /oauth/token, no per-user login or
redirect URI). We look characters up by realm+name, which we already
have, so there's no user-facing login step to build here. The fuller
Authorization Code flow is only needed for /profile/user/wow-style
endpoints tied to a specific logged-in Battle.net account, which this
app doesn't need.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.engine.simc_parser import parse_simc_string
from app.engine import item_icons


@dataclass
class CharacterImportResult:
    """Normalized output of any CharacterDataSource, regardless of
    where the data actually came from."""
    gear: dict = field(default_factory=dict)
    talents: dict = field(default_factory=dict)
    stats_percent: dict = field(default_factory=dict)
    stats_rating: dict = field(default_factory=dict)
    source: str = ""


class CharacterDataSource(ABC):
    """Something that can produce gear/talents/stats for a character.

    `raw_input` is for paste-based sources (e.g. a SimC export string);
    `character` is the Character model instance, for sources that look
    the character up themselves (e.g. by realm + name via an API).
    Implementations use whichever of the two they need and should
    raise ValueError if the one they need wasn't given.
    """

    @abstractmethod
    def fetch(self, character, raw_input: str | None = None) -> CharacterImportResult:
        raise NotImplementedError


class SimCDataSource(CharacterDataSource):
    """Parses a pasted SimC addon export string. Today's default and
    only working implementation -- see app/engine/simc_parser.py."""

    def fetch(self, character, raw_input: str | None = None) -> CharacterImportResult:
        if not raw_input:
            raise ValueError("SimCDataSource requires a pasted SimC export string.")
        parsed = parse_simc_string(raw_input)
        return CharacterImportResult(
            gear=parsed["gear"],
            talents={
                "raw_talent_string": parsed["talents_string"],
                "spec_hint": parsed["spec_hint"],
                "level": parsed["level"],
                "race": parsed["race"],
            },
            stats_percent=parsed["stats_percent"],
            stats_rating=parsed["stats_rating"],
            source="simc",
        )


class BlizzardAPIDataSource(CharacterDataSource):
    """Not implemented yet -- Blizzard developer portal access is
    blocked behind phone/SMS verification. Once that unblocks:

    1. POST https://oauth.battle.net/token with client_credentials grant
       (client id/secret only -- no redirect URI, no browser login) to
       get an app-scoped access token.
    2. GET .../profile/wow/character/{realm-slug}/{character-name}/equipment
       and .../character-statistics, using character.server (slugified)
       and character.name.
    3. Map the response shape into gear/stats_percent the same way
       SimCDataSource does, so callers don't need to change.
    """

    def fetch(self, character, raw_input: str | None = None) -> CharacterImportResult:
        raise NotImplementedError(
            "Blizzard API access isn't set up yet (blocked on developer portal "
            "verification). Use CHARACTER_DATA_SOURCE=simc for now."
        )


def get_character_data_source(name: str) -> CharacterDataSource:
    sources = {
        "simc": SimCDataSource,
        "blizzard": BlizzardAPIDataSource,
    }
    try:
        return sources[name]()
    except KeyError:
        raise ValueError(f"Unknown CHARACTER_DATA_SOURCE {name!r}; expected one of {sorted(sources)}")


class IconSource(ABC):
    """Something that can resolve an item ID to a locally-cached icon
    image filename (relative to the app's static/icons/ directory), or
    None if it couldn't be resolved (the caller falls back to a bundled
    placeholder)."""

    @abstractmethod
    def get_icon_filename(self, item_id, instance_path: str, static_icons_dir: str) -> str | None:
        raise NotImplementedError


class WowheadIconSource(IconSource):
    """Scrapes Wowhead's item page for the icon name, caches it, then
    downloads + caches the actual image from Wowhead's zamimg CDN. See
    app/engine/item_icons.py."""

    def get_icon_filename(self, item_id, instance_path: str, static_icons_dir: str) -> str | None:
        return item_icons.get_item_icon_filename(item_id, instance_path, static_icons_dir)


class BlizzardMediaIconSource(IconSource):
    """Not implemented yet -- same Blizzard API blocker as
    BlizzardAPIDataSource above. Once unblocked, this would call the
    Game Data media endpoint for the item and cache its icon image
    locally the same way WowheadIconSource does, dropping the Wowhead
    CDN dependency entirely."""

    def get_icon_filename(self, item_id, instance_path: str, static_icons_dir: str) -> str | None:
        raise NotImplementedError(
            "Blizzard API access isn't set up yet (blocked on developer portal "
            "verification). Use ICON_SOURCE=wowhead for now."
        )


def get_icon_source(name: str) -> IconSource:
    sources = {
        "wowhead": WowheadIconSource,
        "blizzard": BlizzardMediaIconSource,
    }
    try:
        return sources[name]()
    except KeyError:
        raise ValueError(f"Unknown ICON_SOURCE {name!r}; expected one of {sorted(sources)}")
