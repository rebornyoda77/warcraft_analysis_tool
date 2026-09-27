import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Matches the port sequence used by this Pi's other standalone Flask
# tools (budget_tool: 5000, home_workout_template_generator: 5050).
DEFAULT_PORT = 5060


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'wow_toolkit.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Which CharacterDataSource/IconSource implementation to use (see
    # app/engine/data_sources.py). Swap to "blizzard" once official API
    # access unblocks -- everything that calls get_character_data_source()/
    # get_icon_source() stays the same either way.
    CHARACTER_DATA_SOURCE = os.environ.get("CHARACTER_DATA_SOURCE", "simc")
    ICON_SOURCE = os.environ.get("ICON_SOURCE", "wowhead")
