from flask import Blueprint, render_template, request, redirect, url_for, flash

from app.models.db import db
from app.models.character import Character, CharacterStats
from app.engine.simc_parser import parse_simc_string

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
    return render_template("characters/show.html", character=character)


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
