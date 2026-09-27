#!/usr/bin/env python3
"""One-off, idempotent fixup for SQLite databases created before a model
gained new columns. There's no migration tool (Alembic/Flask-Migrate) set
up yet, so db.create_all() alone won't add columns to an existing table --
it only creates tables that don't exist yet. Run this after a `git pull`
whenever the app fails to start (or a query 500s) with "no such column".

Safe to re-run: it checks each table's existing columns first and only
ALTERs in what's missing.
"""

import os
import sqlite3
import sys

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "instance", "wow_toolkit.db")

COLUMNS_TO_ENSURE = {
    "characters": [
        ("gear", "JSON"),
        ("simc_import_raw", "TEXT"),
        ("character_media", "VARCHAR(255)"),
    ],
    "sim_runs": [
        ("source", "VARCHAR(16) NOT NULL DEFAULT 'internal'"),
        ("sim_type", "VARCHAR(16) NOT NULL DEFAULT 'single_actor'"),
        ("external_report_id", "VARCHAR(64)"),
        ("external_url", "VARCHAR(512)"),
    ],
}


def main():
    if not os.path.exists(DB_PATH):
        print(f"No database at {DB_PATH} -- nothing to migrate (it'll be created fresh on next run).")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for table, columns in COLUMNS_TO_ENSURE.items():
        cursor.execute(f"PRAGMA table_info({table})")
        existing = {row[1] for row in cursor.fetchall()}
        if not existing:
            print(f"Table '{table}' doesn't exist yet -- skipping (it'll be created fresh on next run).")
            continue

        for column_name, column_def in columns:
            if column_name in existing:
                print(f"{table}.{column_name} already exists, skipping.")
                continue
            sql = f"ALTER TABLE {table} ADD COLUMN {column_name} {column_def}"
            print(f"Running: {sql}")
            cursor.execute(sql)

    conn.commit()
    conn.close()
    print("Done.")


if __name__ == "__main__":
    sys.exit(main())
