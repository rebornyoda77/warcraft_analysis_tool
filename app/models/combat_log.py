from datetime import datetime, timezone

from app.models.db import db


class CombatLog(db.Model):
    __tablename__ = "combat_logs"

    id = db.Column(db.Integer, primary_key=True)
    character_id = db.Column(db.Integer, db.ForeignKey("characters.id"), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    source_filename = db.Column(db.String(255))
    combat_log_version = db.Column(db.String(16))

    encounters = db.relationship(
        "Encounter", backref="combat_log", cascade="all, delete-orphan"
    )


class Encounter(db.Model):
    __tablename__ = "encounters"

    id = db.Column(db.Integer, primary_key=True)
    combat_log_id = db.Column(db.Integer, db.ForeignKey("combat_logs.id"), nullable=False)
    name = db.Column(db.String(128))
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    encounter_type = db.Column(db.String(16))  # trash / boss
    difficulty = db.Column(db.String(16))  # normal / heroic / mythic
    keystone_level = db.Column(db.Integer, nullable=True)

    events = db.relationship(
        "CombatEvent", backref="encounter", cascade="all, delete-orphan"
    )


class CombatEvent(db.Model):
    __tablename__ = "combat_events"

    id = db.Column(db.Integer, primary_key=True)
    encounter_id = db.Column(db.Integer, db.ForeignKey("encounters.id"), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    event_type = db.Column(db.String(64), nullable=False)
    source = db.Column(db.String(128))
    target = db.Column(db.String(128))
    ability_id = db.Column(db.String(32))
    amount = db.Column(db.Integer)
    overhealing = db.Column(db.Integer)
    is_crit = db.Column(db.Boolean, default=False)

    __table_args__ = (
        db.Index("ix_combat_events_encounter_event_type", "encounter_id", "event_type"),
    )


class SimRun(db.Model):
    __tablename__ = "sim_runs"

    id = db.Column(db.Integer, primary_key=True)
    character_id = db.Column(db.Integer, db.ForeignKey("characters.id"), nullable=False)
    spec = db.Column(db.String(32), nullable=False)
    apl_definition = db.Column(db.JSON, default=dict)
    duration = db.Column(db.Float)
    result_summary = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # "internal" (this app's own simulator, once built) or "raidbots" (an
    # imported report). sim_type further distinguishes a Raidbots
    # single-actor sim (Quick/Advanced Sim) from a profileset sim (Top
    # Gear/Droptimizer), since the latter's result_summary holds a ranked
    # list of combos rather than one result.
    source = db.Column(db.String(16), nullable=False, default="internal")
    sim_type = db.Column(db.String(16), nullable=False, default="single_actor")
    external_report_id = db.Column(db.String(64))
    external_url = db.Column(db.String(512))
