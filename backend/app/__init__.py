from flask import Flask

from app.config.database import init_database
from app.config.settings import load_settings
from app.controller.health import blueprint as health_blueprint


def create_app() -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config.update(load_settings())
    app.logger.setLevel(app.config["LOG_LEVEL"])
    init_database(app)
    app.register_blueprint(health_blueprint)
    return app
