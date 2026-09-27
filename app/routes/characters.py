from flask import Blueprint, render_template, request, redirect, url_for, flash

from app.models.db import db
from app.models.character import Character, CharacterStats

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
