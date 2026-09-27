from flask import Blueprint, render_template

bp = Blueprint("simulator", __name__, url_prefix="/simulator")


@bp.route("/")
def index():
    return render_template("coming_soon.html", feature="Rotation Simulator")
