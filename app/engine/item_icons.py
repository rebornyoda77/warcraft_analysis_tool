"""Item icon name lookup + local icon caching.

WoW items don't carry their icon name in a SimC export (just the item
ID), so this resolves item_id -> icon_name by scraping Wowhead's public
item page, then downloads the actual icon from Wowhead's zamimg CDN and
caches it on local disk so we only ever hit either of those once per
item.

Caveat: built without network access to wowhead.com or wow.zamimg.com
(both blocked in the sandbox this was written in), so the scraping
patterns below are best-effort based on Wowhead's well-known, stable
conventions (Open Graph meta tags, the CDN's icon URL structure) rather
than something tested against a live page. If icons come back wrong or
missing once this runs somewhere with real internet access, this is the
file to fix -- see _extract_icon_name for the actual parsing logic.

Two-level cache, both keyed by a stable, cheap-to-check identity:
  - item_id -> icon_name: a small JSON file (instance/item_icon_cache.json),
    since this is a lightweight lookup table, not relational data.
  - icon_name -> image bytes: files under app/static/icons/<icon_name>.jpg,
    served directly by Flask's static handler once cached.
"""

import json
import os
import re
import threading

import requests

FALLBACK_ICON_NAME = "inv_misc_questionmark"

ICON_URL_TEMPLATE = "https://wow.zamimg.com/images/wow/icons/large/{icon_name}.jpg"

# Tried in order; the first one that yields a plausible icon name wins.
ITEM_PAGE_URL_TEMPLATES = [
    "https://www.wowhead.com/item={item_id}",
    "https://nether.wowhead.com/item={item_id}",
]

_ICON_NAME_PATTERNS = [
    # Open Graph image meta tag -- a stable, non-Wowhead-specific
    # convention, so the least likely of these to break across a
    # Wowhead redesign.
    re.compile(r'property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', re.IGNORECASE),
    # Wowhead's own tooltip/icon data embedded in the page as JSON.
    re.compile(r'"icon"\s*:\s*"([a-z0-9_\-]+)"', re.IGNORECASE),
]
_ICON_FILENAME_FROM_URL = re.compile(
    r"/icons/(?:tiny|small|medium|large)/([a-z0-9_\-]+)\.(?:jpg|jpeg|png|gif)",
    re.IGNORECASE,
)

_cache_lock = threading.Lock()


def _cache_path(instance_path):
    return os.path.join(instance_path, "item_icon_cache.json")


def _load_cache(instance_path):
    path = _cache_path(instance_path)
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except (ValueError, OSError):
        return {}


def _save_cache(instance_path, cache):
    path = _cache_path(instance_path)
    with open(path, "w") as f:
        json.dump(cache, f, indent=2, sort_keys=True)


def _extract_icon_name(text):
    for pattern in _ICON_NAME_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        candidate = match.group(1)
        # The og:image pattern captures a full URL; pull the icon
        # filename out of it. The JSON pattern already captures a bare
        # icon name.
        url_match = _ICON_FILENAME_FROM_URL.search(candidate)
        if url_match:
            return url_match.group(1)
        if re.match(r"^[a-z0-9_\-]+$", candidate, re.IGNORECASE):
            return candidate
    return None


def resolve_icon_name(item_id, instance_path, timeout=10):
    """Look up an item's icon name, using the on-disk cache first."""
    item_id = str(item_id)
    with _cache_lock:
        cache = _load_cache(instance_path)
        if item_id in cache:
            return cache[item_id]

    icon_name = None
    for template in ITEM_PAGE_URL_TEMPLATES:
        url = template.format(item_id=item_id)
        try:
            response = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
            icon_name = _extract_icon_name(response.text)
            if icon_name:
                break
        except requests.RequestException:
            continue

    icon_name = icon_name or FALLBACK_ICON_NAME

    with _cache_lock:
        cache = _load_cache(instance_path)
        cache[item_id] = icon_name
        _save_cache(instance_path, cache)

    return icon_name


def ensure_icon_downloaded(icon_name, static_icons_dir, timeout=10):
    """Download an icon's image to static_icons_dir if not already
    cached there. Returns the local filename (not full path)."""
    filename = f"{icon_name}.jpg"
    local_path = os.path.join(static_icons_dir, filename)
    if os.path.exists(local_path):
        return filename

    os.makedirs(static_icons_dir, exist_ok=True)
    url = ICON_URL_TEMPLATE.format(icon_name=icon_name)
    try:
        response = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        with open(local_path, "wb") as f:
            f.write(response.content)
    except requests.RequestException:
        if icon_name != FALLBACK_ICON_NAME:
            return ensure_icon_downloaded(FALLBACK_ICON_NAME, static_icons_dir, timeout=timeout)
        return None

    return filename


def get_item_icon_filename(item_id, instance_path, static_icons_dir):
    """End-to-end: item_id -> locally-cached icon filename, resolving
    and downloading as needed. This is what routes/templates call."""
    icon_name = resolve_icon_name(item_id, instance_path)
    return ensure_icon_downloaded(icon_name, static_icons_dir)
