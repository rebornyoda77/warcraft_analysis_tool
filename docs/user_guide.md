# WoW Toolkit — User Guide

A personal WoW Retail toolkit: character roster with gear/talent/stat
import, combat log analysis (planned), a rotation simulator (planned),
and a stat-weight calculator (planned). Runs as a standalone Flask app
on DarthPi, alongside `budget_tool` and `home_workout_template_generator`.

## Setup

```bash
git clone https://github.com/rebornyoda77/warcraft_analysis_tool.git wow-toolkit
cd wow-toolkit
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create the database (see [Database migrations](#database-migrations) below
for what this actually does):

```bash
export FLASK_APP=app
flask db upgrade
```

Run it once by hand to confirm it works:

```bash
python run.py
```

This starts the app on `http://127.0.0.1:5060` by default. Leave it running
and open that URL from another terminal/browser, or `Ctrl+C` once you've
confirmed it starts without errors.

```bash
python run.py --help          # see all options
python run.py --port 5061     # different port
python run.py --debug         # Flask's reloader/debugger, dev only
```

## Deploying on a server (e.g. this Pi)

**1. Install as a systemd service**, so it survives reboots and restarts
itself if it crashes:

```bash
sudo cp deploy/wow-toolkit-web.service /etc/systemd/system/
sudo nano /etc/systemd/system/wow-toolkit-web.service   # edit User=/WorkingDirectory= to match your setup
sudo systemctl daemon-reload
sudo systemctl enable --now wow-toolkit-web
```

Check it came up with `sudo systemctl status wow-toolkit-web`, and
`journalctl -u wow-toolkit-web -f` to watch its logs live.

**2. Expose it.** The service file documents two options right in its
comments:

- **Option A (default): Tailscale.** The service binds to `127.0.0.1` —
  nothing on your LAN can reach the app directly. Run
  `sudo tailscale serve --bg 5060` once, and it's reachable at
  `https://<this-machine>.<tailnet>.ts.net` from any device on your
  tailnet, with real HTTPS, no port forwarding.
- **Option B: a reverse proxy (e.g. Nginx Proxy Manager).** If NPM runs
  in its own Docker container, its `127.0.0.1` is the *container's*
  loopback, not the Pi's — it can only reach this app via the Pi's real
  LAN IP. That means the app needs to bind `0.0.0.0` instead. In the
  service file, comment out the Option A `ExecStart` line and uncomment
  Option B (`--host 0.0.0.0`), then:
  ```bash
  sudo systemctl daemon-reload
  sudo systemctl restart wow-toolkit-web
  ```
  Point NPM's proxy host at the Pi's LAN IP and port `5060` (**not**
  `127.0.0.1`/`localhost` — that's the container's own loopback).

  **This is what this Pi's install actually uses.** Since 0.0.0.0 means
  anything else on the LAN could otherwise reach the app directly too,
  it's restricted at the firewall to just NPM's Docker subnet (matching
  the same rules already in place for `budget_tool` and
  `home_workout_template_generator`):
  ```bash
  sudo ufw allow from 172.21.0.0/16 to any port 5060 proto tcp
  ```
  If you ever see a **504 Gateway Timeout** from NPM/openresty on this
  app, check in this order: (1) is the service actually running
  (`sudo systemctl status wow-toolkit-web`)? (2) is it bound to `0.0.0.0`,
  not `127.0.0.1` (check the log line `Running on http://...`)? (3) does
  `sudo ufw status` have the `5060/tcp ALLOW 172.21.0.0/16` rule? All
  three tripped this exact error during initial setup.

### Restarting after changes

```bash
sudo systemctl restart wow-toolkit-web
```

Do this after: pulling new code, editing the `.service` file (also run
`daemon-reload` first), or if something looks stuck. After a `git pull`,
also run these two **before** restarting, in case they changed:

```bash
source venv/bin/activate
pip install -r requirements.txt   # new/updated dependencies
flask db upgrade                  # new database columns/tables (see below)
```

Forgetting either of these is the most common cause of the service
crash-looping right after a pull — check `journalctl -u wow-toolkit-web -n 30`
for `ModuleNotFoundError` (missing pip install) or
`sqlalchemy.exc.OperationalError: no such column` (missing migration).

## Database migrations

This app uses Flask-Migrate (Alembic under the hood) to manage the SQLite
schema. `FLASK_APP=app` lets the `flask` CLI find the app automatically
(it auto-detects the `create_app` factory in `app/__init__.py`) — export
that once per shell session before running any `flask db ...` command,
or set it permanently in the venv's `activate` script.

**After pulling new code**, always run:
```bash
export FLASK_APP=app
flask db upgrade
```
This applies any new migrations without touching your existing data.
It's always safe to re-run — a migration that's already applied is a
no-op.

**If a model changes** (only relevant if you're developing, not just
running the app), the workflow is:
```bash
export FLASK_APP=app
flask db migrate -m "describe the change"   # autogenerates a migration
flask db upgrade                            # applies it locally
```
Commit the generated file under `migrations/versions/` along with the
model change.

## Features

### Characters

**Characters → + New Character** creates a roster entry (name, class,
spec, faction, server, notes). Click a character's **name** (not
"Edit") to get to its detail page, where gear/stat import, sim-run
history, and manual stat overrides all live.

**One character record per spec.** If you play multiple specs on one
character (e.g. Elemental and Restoration), create a separate character
entry for each — gear/talents/stats get overwritten on every import, so
one record can't hold two specs' loadouts at once.

### Importing gear/talents/stats (SimC addon string)

1. In-game, install the SimulationCraft addon (in-game addon browser, or
   manually from simulationcraft.org into `Interface/AddOns/`).
2. On your character, out of combat, type `/simc` — a window pops up
   with the export text pre-copied to your clipboard.
3. On the character's page in this app, paste it into **Import from SimC
   Addon String** and click **Import**.

This populates the parsed gear table (item/bonus/gem/enchant IDs, with
Wowhead-sourced icons), the talent string, and — only if the export
happened to include them — current stat percentages. **Standard SimC
exports usually don't include haste/crit/mastery/versatility
percentages** (SimC's own sim engine computes those from gear, it
doesn't just report them), so don't be surprised if **Stats** stays at
0.0 after import. Fill those in manually from your character pane below
the import box; manual entry always overrides whatever the import set.

### Importing sim results (Raidbots)

This app never submits sims to Raidbots — there's no public API for
that. The workflow is: run a sim yourself on raidbots.com, then paste
the report's URL (or its raw JSON, as a fallback if the URL fetch
doesn't work) into **Import Sim Results** on the character page. Handles
both single-actor (Quick/Advanced Sim) and profileset (Top Gear/
Droptimizer) report shapes, tagged and shown in the **Sim Runs** table
alongside this app's own simulator output once that's built.

### Item icons

Gear table icons are scraped from Wowhead's public item page and cached
locally (`app/static/icons/`, gitignored) — nothing needed on your end,
this happens automatically the first time a given item ID is displayed.
If an icon fails to resolve, a placeholder "?" icon shows instead of a
broken image.

## Data sources: today vs. future (Blizzard API)

Gear/stat import and icon lookup both go through a swappable interface
(`app/engine/data_sources.py`), selected via `config.py`'s
`CHARACTER_DATA_SOURCE` and `ICON_SOURCE` settings (default: `simc` and
`wowhead`).

The plan is to add official Blizzard Game Data API support once
developer portal access unblocks (currently stuck behind phone/SMS
verification) — equipment/stats via the Profile API, item icons via the
Game Data media endpoint, and a full character render/portrait (the
`character_media` column already exists on `Character`, unpopulated
until then). That only needs the simple OAuth2 client-credentials flow
(one app-scoped token, no per-user login), since characters are looked
up by realm + name rather than a logged-in Battle.net account. When that
lands, it's a new class in `data_sources.py` plus a config value change
— not a rewrite of the routes or templates.

## Project structure

```
app/
  routes/       Flask blueprints (characters, logs, simulator, stats, icons)
  models/       SQLAlchemy models
  engine/       Spec-agnostic logic: SimC parsing, Raidbots parsing,
                icon caching, the data-source abstraction. Will also hold
                the ability-YAML loader and simulator core once built.
  data/specs/   Class/spec ability definitions (YAML), not yet populated
  templates/, static/
migrations/     Flask-Migrate/Alembic migrations
deploy/         systemd service file
```

`engine/simulator.py` and `engine/log_parser.py` (once built) are meant
to be spec-agnostic — they'll only know generic Ability/Resource/Event
objects loaded from YAML, so adding a new class/spec later means adding
a YAML file, not touching engine code.

## What's built vs. planned

- ✅ Character CRUD, SimC import, Raidbots sim import, item icon caching
- ⬜ Combat log parser (`engine/log_parser.py`) — needs a real
  `WoWCombatLog.txt` to build/test against
- ⬜ Encounter dashboard (timeline chart, ability breakdown, buff/debuff
  uptime)
- ⬜ Ability YAML loader + `shaman_restoration.yaml`
- ⬜ Simulator engine
- ⬜ Stat-weight driver
