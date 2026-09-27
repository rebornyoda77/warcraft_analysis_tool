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
