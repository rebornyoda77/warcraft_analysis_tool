import os

from flask import Flask, render_template

from config import Config
from app.models.db import db


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)

    from app.routes import characters, logs, simulator, stats

    app.register_blueprint(characters.bp)
    app.register_blueprint(logs.bp)
    app.register_blueprint(simulator.bp)
    app.register_blueprint(stats.bp)

    @app.route("/")
    def home():
        return render_template("home.html")

    with app.app_context():
        db.create_all()

    return app
