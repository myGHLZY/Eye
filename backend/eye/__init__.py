from flask import Flask

from eye.config.settings import load_settings
from eye.controller.health import blueprint as health_blueprint


def create_app() -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config.update(load_settings())
    app.logger.setLevel(app.config["LOG_LEVEL"])
    app.register_blueprint(health_blueprint)
    return app
