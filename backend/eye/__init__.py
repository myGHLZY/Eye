from flask import Flask

from eye.cli import check_database
from eye.config.database import init_database
from eye.config.settings import load_settings
from eye.controller.health import blueprint as health_blueprint


def create_app() -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config.update(load_settings())
    app.logger.setLevel(app.config["LOG_LEVEL"])
    init_database(app)
    app.cli.add_command(check_database)
    app.register_blueprint(health_blueprint)
    return app
