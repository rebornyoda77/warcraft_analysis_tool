"""Parser for SimulationCraft addon export strings.

The in-game "SimC" addon (`/simc`) copies a text block to the clipboard
with one `key=value` (or bare `key=`) directive per line, plus a leading
comment header like `# CharacterName - Spec - Realm`. Gear slots are their
own directives, e.g.:

    head=,id=207166,bonus_id=6652/8767/1524,gem_id=213747,enchant_id=7361

This module only understands that text shape — it knows nothing about
Flask, SQLAlchemy, or any particular class/spec. It hands back plain
dicts for the caller to persist however it likes.
"""

import re

GEAR_SLOTS = {
    "head", "neck", "shoulder", "shoulders", "back", "chest", "shirt",
    "tabard", "wrist", "hands", "waist", "legs", "feet", "finger1",
    "finger2", "trinket1", "trinket2", "main_hand", "off_hand",
}

# Stat directives some addon/export variants emit directly as a rating
# or a percentage. Ratings alone can't be turned into a percentage
# without level- and class-specific constants, so those are reported
# as ratings and left for manual entry/override to resolve into the
# in-game percentage.
STAT_RATING_KEYS = {
    "haste_rating": "haste",
    "crit_rating": "crit",
    "mastery_rating": "mastery",
    "versatility_rating": "versatility",
}
STAT_PERCENT_KEYS = {
    "haste": "haste",
    "crit": "crit",
    "mastery": "mastery",
    "versatility": "versatility",
}

HEADER_RE = re.compile(r"^#\s*(?P<name>[^-#]+?)\s*-\s*(?P<spec>[^-#]+?)\s*-\s*(?P<realm>[^-#]+?)\s*$")
GEAR_ATTR_RE = re.compile(r"(\w+)=([^,]*)")


def parse_simc_string(raw_text):
    """Parse a raw SimC addon export into a structured dict.

    Returns:
        {
            "character_name": str | None,
            "spec_hint": str | None,
            "realm_hint": str | None,
            "level": int | None,
            "race": str | None,
            "talents_string": str | None,
            "gear": {slot: {"id": ..., "bonus_id": ..., "gem_id": ..., "enchant_id": ..., "ilevel": ...}},
            "stats_rating": {"haste": int, ...},   # raw ratings, unconverted
            "stats_percent": {"haste": float, ...},  # only if the export gave percentages directly
            "raw_fields": {key: value},  # every top-level key=value directive seen
        }
    """
    result = {
        "character_name": None,
        "spec_hint": None,
        "realm_hint": None,
        "level": None,
        "race": None,
        "talents_string": None,
        "gear": {},
        "stats_rating": {},
        "stats_percent": {},
        "raw_fields": {},
    }

    if not raw_text:
        return result

    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue

        if line.startswith("#"):
            header = HEADER_RE.match(line)
            if header and result["character_name"] is None:
                result["character_name"] = header.group("name").strip()
                result["spec_hint"] = header.group("spec").strip()
                result["realm_hint"] = header.group("realm").strip()
            continue

        if "=" not in line:
            continue

        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()

        slot = key.lower()
        if slot in GEAR_SLOTS:
            result["gear"][slot] = _parse_gear_directive(value)
            continue

        result["raw_fields"][key] = value

        if key == "level" and value.isdigit():
            result["level"] = int(value)
        elif key == "race":
            result["race"] = value
        elif key == "talents":
            result["talents_string"] = value
        elif key in STAT_RATING_KEYS and value.replace(".", "", 1).isdigit():
            result["stats_rating"][STAT_RATING_KEYS[key]] = float(value)
        elif key in STAT_PERCENT_KEYS:
            match = re.match(r"([\d.]+)", value)
            if match:
                result["stats_percent"][STAT_PERCENT_KEYS[key]] = float(match.group(1))

    return result


def _parse_gear_directive(value):
    """Parse the comma-separated attribute list of a gear slot's value.

    e.g. ",id=207166,bonus_id=6652/8767/1524,gem_id=213747,enchant_id=7361"
    -> {"id": "207166", "bonus_id": "6652/8767/1524", "gem_id": "213747", "enchant_id": "7361"}
    """
    attrs = {}
    for match in GEAR_ATTR_RE.finditer(value):
        attrs[match.group(1)] = match.group(2)
    return attrs
