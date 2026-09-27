from flask import Blueprint, render_template

bp = Blueprint("logs", __name__, url_prefix="/logs")


@bp.route("/")
def index():
    return render_template("coming_soon.html", feature="Combat Log Analyzer")
