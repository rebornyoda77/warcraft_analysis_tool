"""Importer for already-run Raidbots.com sim reports.

Raidbots has no public API to submit a sim job — this module only
CONSUMES a report you already ran on raidbots.com yourself: you paste
the report's URL (or bare report ID) here, and this fetches and parses
that report's underlying JSON.

Caveat: the exact JSON shape below is built from public knowledge of
Raidbots' report format, not verified against a live fetch (this was
built somewhere without network access to raidbots.com). If a real
report doesn't parse cleanly, fetch_report_json() also accepts raw JSON
text pasted directly -- copy it from the report page's "Advanced" ->
raw JSON view, or however Raidbots currently exposes it -- as a
guaranteed-to-work fallback while the field-name guesses below get
corrected against real data.
"""

import json
import re

import requests

REPORT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{10,40}$")
REPORT_URL_RE = re.compile(r"raidbots\.com/simbot/report/([A-Za-z0-9_-]+)")

# Best-effort guesses at where Raidbots exposes a report's raw JSON.
# Tried in order; the first one that returns valid JSON wins.
CANDIDATE_JSON_URL_TEMPLATES = [
    "https://www.raidbots.com/simbot/report/{report_id}.json",
    "https://www.raidbots.com/reports/{report_id}/data.json",
    "https://data.raidbots.com/reports/{report_id}.json",
]


class RaidbotsImportError(Exception):
    pass


def extract_report_id(url_or_id):
    """Pull a bare report ID out of a full Raidbots URL, or pass through
    a string that already looks like one."""
    url_or_id = url_or_id.strip()
    match = REPORT_URL_RE.search(url_or_id)
    if match:
        return match.group(1)
    if REPORT_ID_RE.match(url_or_id):
        return url_or_id
    raise RaidbotsImportError(
        f"Doesn't look like a Raidbots report URL or ID: {url_or_id!r}"
    )


def fetch_report_json(url_or_id, timeout=15):
    """Fetch a report's raw JSON from raidbots.com by trying each
    candidate endpoint in turn. Raises RaidbotsImportError with the
    attempted URLs if none of them work -- at that point, paste the
    report's raw JSON directly into parse_report() instead."""
    report_id = extract_report_id(url_or_id)
    errors = []
    for template in CANDIDATE_JSON_URL_TEMPLATES:
        candidate_url = template.format(report_id=report_id)
        try:
            response = requests.get(candidate_url, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            errors.append(f"{candidate_url}: {exc}")
            continue
    raise RaidbotsImportError(
        "Couldn't fetch this report from any known Raidbots endpoint:\n"
        + "\n".join(errors)
        + "\n\nPaste the report's raw JSON directly instead as a fallback."
    )


def parse_report(raw_json, report_id=None, report_url=None):
    """Normalize a Raidbots report's raw JSON into a dict this app can
    store in a SimRun row. Detects single-actor (Quick/Advanced Sim) vs.
    profileset (Top Gear/Droptimizer) reports and shapes the summary
    differently for each.

    Field-name guesses are defensive (multiple fallback keys tried) since
    this was written without a live report to test against -- see the
    module docstring.
    """
    if isinstance(raw_json, str):
        try:
            raw_json = json.loads(raw_json)
        except ValueError as exc:
            raise RaidbotsImportError(f"That doesn't look like valid JSON: {exc}")

    sim = raw_json.get("sim", raw_json)

    profilesets = _first_present(sim, ["profilesets", "profileset_results"])
    if profilesets:
        return _parse_profileset_report(sim, profilesets, report_id, report_url)
    return _parse_single_actor_report(sim, report_id, report_url)


def _parse_single_actor_report(sim, report_id, report_url):
    players = _first_present(sim, ["players", "actors"]) or []
    if not players:
        raise RaidbotsImportError(
            "Couldn't find any player/actor data in this report. Top-level "
            f"keys seen: {sorted(sim.keys())}"
        )
    player = players[0]
    collected = player.get("collected_data", {})

    dps = _metric_mean(collected, ["dps", "DPS"])
    hps = _metric_mean(collected, ["hps", "HPS"])

    ability_breakdown = []
    for name, stats in (player.get("stats_by_action") or player.get("abilities") or {}).items():
        if isinstance(stats, dict):
            ability_breakdown.append({
                "name": name,
                "total": stats.get("total") or stats.get("actual_amount"),
                "count": stats.get("count") or stats.get("num_executes"),
            })

    buff_uptimes = {}
    for buff in player.get("buffs", []) or []:
        name = buff.get("name")
        uptime = buff.get("uptime_pct") or buff.get("uptime")
        if name is not None and uptime is not None:
            buff_uptimes[name] = uptime

    return {
        "sim_type": "single_actor",
        "source": "raidbots",
        "external_report_id": report_id,
        "external_url": report_url,
        "spec": player.get("specialization") or player.get("spec"),
        "duration": _first_present(sim, ["max_time", "duration"]),
        "result_summary": {
            "actor_name": player.get("name"),
            "dps": dps,
            "hps": hps,
            "ability_breakdown": ability_breakdown,
            "buff_uptimes": buff_uptimes,
        },
    }


def _parse_profileset_report(sim, profilesets, report_id, report_url):
    combos = []
    results = profilesets if isinstance(profilesets, list) else profilesets.get("results", [])
    for entry in results:
        combos.append({
            "name": entry.get("name"),
            "mean": entry.get("mean"),
            "median": entry.get("median"),
            "min": entry.get("min"),
            "max": entry.get("max"),
        })
    combos.sort(key=lambda c: c["mean"] or 0, reverse=True)

    return {
        "sim_type": "profileset",
        "source": "raidbots",
        "external_report_id": report_id,
        "external_url": report_url,
        "spec": None,
        "duration": _first_present(sim, ["max_time", "duration"]),
        "result_summary": {
            "baseline": _first_present(sim, ["sim", "baseline"]),
            "combos": combos,
        },
    }


def _first_present(d, keys):
    for key in keys:
        if isinstance(d, dict) and d.get(key) is not None:
            return d[key]
    return None


def _metric_mean(collected, keys):
    for key in keys:
        metric = collected.get(key)
        if isinstance(metric, dict):
            return metric.get("mean")
        if isinstance(metric, (int, float)):
            return metric
    return None
