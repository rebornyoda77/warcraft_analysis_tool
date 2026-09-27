from flask import Blueprint, render_template, request, redirect, url_for, flash

from app.models.db import db
from app.models.character import Character, CharacterStats
from app.models.combat_log import SimRun
from app.engine.simc_parser import parse_simc_string
from app.engine.raidbots_importer import (
    RaidbotsImportError,
    extract_report_id,
    fetch_report_json,
    parse_report,
)

bp = Blueprint("characters", __name__, url_prefix="/characters")

CLASS_SPECS = {
    "shaman": ["restoration", "enhancement", "elemental"],
}


@bp.route("/")
def index():
    characters = Character.query.order_by(Character.name).all()
    return render_template("characters/index.html", characters=characters)


@bp.route("/new", methods=["GET", "POST"])
def new():
    if request.method == "POST":
        character = Character(
            name=request.form["name"].strip(),
            char_class=request.form["char_class"],
            spec=request.form["spec"],
            faction=request.form.get("faction") or None,
            server=request.form.get("server") or None,
            notes=request.form.get("notes") or None,
        )
        db.session.add(character)
        db.session.flush()
        db.session.add(CharacterStats(character_id=character.id))
        db.session.commit()
        flash(f"Created character {character.name}", "success")
        return redirect(url_for("characters.index"))
    return render_template("characters/form.html", character=None, class_specs=CLASS_SPECS)


@bp.route("/<int:character_id>")
def show(character_id):
    character = Character.query.get_or_404(character_id)
    sim_runs = (
        SimRun.query.filter_by(character_id=character.id)
        .order_by(SimRun.created_at.desc())
        .all()
    )
    return render_template("characters/show.html", character=character, sim_runs=sim_runs)


@bp.route("/<int:character_id>/edit", methods=["GET", "POST"])
def edit(character_id):
    character = Character.query.get_or_404(character_id)
    if request.method == "POST":
        character.name = request.form["name"].strip()
        character.char_class = request.form["char_class"]
        character.spec = request.form["spec"]
        character.faction = request.form.get("faction") or None
        character.server = request.form.get("server") or None
        character.notes = request.form.get("notes") or None
        db.session.commit()
        flash(f"Updated character {character.name}", "success")
        return redirect(url_for("characters.show", character_id=character.id))
    return render_template("characters/form.html", character=character, class_specs=CLASS_SPECS)


@bp.route("/<int:character_id>/delete", methods=["POST"])
def delete(character_id):
    character = Character.query.get_or_404(character_id)
    db.session.delete(character)
    db.session.commit()
    flash(f"Deleted character {character.name}", "success")
    return redirect(url_for("characters.index"))


@bp.route("/<int:character_id>/import_simc", methods=["POST"])
def import_simc(character_id):
    character = Character.query.get_or_404(character_id)
    raw_text = request.form.get("simc_string", "").strip()
    if not raw_text:
        flash("Paste a SimC addon export string first.", "error")
        return redirect(url_for("characters.show", character_id=character.id))

    parsed = parse_simc_string(raw_text)

    character.simc_import_raw = raw_text
    character.gear = parsed["gear"]
    character.talents = {
        "raw_talent_string": parsed["talents_string"],
        "spec_hint": parsed["spec_hint"],
        "level": parsed["level"],
        "race": parsed["race"],
    }

    applied_stats = []
    if parsed["stats_percent"]:
        stats = character.stats or CharacterStats(character_id=character.id)
        for field, value in parsed["stats_percent"].items():
            setattr(stats, field, value)
            applied_stats.append(field)
        db.session.add(stats)

    db.session.commit()

    summary = [f"{len(parsed['gear'])} gear slots"]
    if parsed["talents_string"]:
        summary.append("talents")
    if applied_stats:
        summary.append(f"stats ({', '.join(applied_stats)})")
    elif parsed["stats_rating"]:
        summary.append(
            "stat ratings found but not applied — SimC exports don't include "
            "in-game percentages; enter them manually below"
        )
    flash(f"Imported from SimC string: {', '.join(summary)}.", "success")
    return redirect(url_for("characters.show", character_id=character.id))


@bp.route("/<int:character_id>/import_raidbots", methods=["POST"])
def import_raidbots(character_id):
    character = Character.query.get_or_404(character_id)

    url_or_id = request.form.get("raidbots_url", "").strip()
    raw_json_text = request.form.get("raidbots_json", "").strip()

    try:
        if raw_json_text:
            report_id = extract_report_id(url_or_id) if url_or_id else None
            parsed = parse_report(raw_json_text, report_id=report_id, report_url=url_or_id or None)
        elif url_or_id:
            report_id = extract_report_id(url_or_id)
            raw_json = fetch_report_json(url_or_id)
            parsed = parse_report(raw_json, report_id=report_id, report_url=url_or_id)
        else:
            flash("Paste a Raidbots report URL/ID, or its raw JSON, first.", "error")
            return redirect(url_for("characters.show", character_id=character.id))
    except RaidbotsImportError as exc:
        flash(f"Couldn't import that Raidbots report: {exc}", "error")
        return redirect(url_for("characters.show", character_id=character.id))

    sim_run = SimRun(
        character_id=character.id,
        spec=parsed["spec"] or character.spec,
        duration=parsed["duration"],
        result_summary=parsed["result_summary"],
        source=parsed["source"],
        sim_type=parsed["sim_type"],
        external_report_id=parsed["external_report_id"],
        external_url=parsed["external_url"],
    )
    db.session.add(sim_run)
    db.session.commit()

    flash(f"Imported {parsed['sim_type'].replace('_', ' ')} report from Raidbots.", "success")
    return redirect(url_for("characters.show", character_id=character.id))


@bp.route("/<int:character_id>/stats", methods=["POST"])
def update_stats(character_id):
    character = Character.query.get_or_404(character_id)
    stats = character.stats or CharacterStats(character_id=character.id)
    stats.haste = float(request.form.get("haste") or 0)
    stats.crit = float(request.form.get("crit") or 0)
    stats.hit = float(request.form.get("hit") or 0)
    stats.mastery = float(request.form.get("mastery") or 0)
    stats.versatility = float(request.form.get("versatility") or 0)
    db.session.add(stats)
    db.session.commit()
    flash("Stats updated", "success")
    return redirect(url_for("characters.show", character_id=character.id))
