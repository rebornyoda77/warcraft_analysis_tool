import os

from flask import Blueprint, current_app, send_from_directory

from app.engine.data_sources import get_icon_source

bp = Blueprint("icons", __name__, url_prefix="/icons")


def _static_icons_dir():
    return os.path.join(current_app.static_folder, "icons")


@bp.route("/item/<int:item_id>")
def item_icon(item_id):
    source = get_icon_source(current_app.config["ICON_SOURCE"])
    filename = source.get_icon_filename(
        item_id,
        instance_path=current_app.instance_path,
        static_icons_dir=_static_icons_dir(),
    )
    if filename is None:
        return send_from_directory(_static_icons_dir(), "_placeholder.svg")
    return send_from_directory(_static_icons_dir(), filename)
