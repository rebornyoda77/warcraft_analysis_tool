from datetime import datetime, timezone

from app.models.db import db


class Character(db.Model):
    __tablename__ = "characters"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    char_class = db.Column("class", db.String(32), nullable=False)
    spec = db.Column(db.String(32), nullable=False)
    faction = db.Column(db.String(16))
    server = db.Column(db.String(64))
    talents = db.Column(db.JSON, default=dict)
    notes = db.Column(db.Text)

    stats = db.relationship(
        "CharacterStats",
        backref="character",
        uselist=False,
        cascade="all, delete-orphan",
    )
    combat_logs = db.relationship(
        "CombatLog", backref="character", cascade="all, delete-orphan"
    )
    sim_runs = db.relationship(
        "SimRun", backref="character", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Character {self.name} ({self.char_class}/{self.spec})>"


class CharacterStats(db.Model):
    __tablename__ = "character_stats"

    character_id = db.Column(
        db.Integer, db.ForeignKey("characters.id"), primary_key=True
    )
    haste = db.Column(db.Float, default=0)
    crit = db.Column(db.Float, default=0)
    hit = db.Column(db.Float, default=0)
    mastery = db.Column(db.Float, default=0)
    versatility = db.Column(db.Float, default=0)
    updated_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )
