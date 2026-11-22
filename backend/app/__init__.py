from flask import Flask, request

from app.config.settings import load_settings
from app.controller.database import blueprint as database_blueprint
from app.controller.health import blueprint as health_blueprint
from app.database.database import init_database


def create_app() -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config.update(load_settings())
    app.logger.setLevel(app.config["LOG_LEVEL"])
    init_database(app)
    app.register_blueprint(health_blueprint)
    app.register_blueprint(database_blueprint)

    @app.before_request
    def log_request() -> None:
        app.logger.info(
            "port=%s %s %r",
            request.environ.get("SERVER_PORT", "?"),
            request.method,
            request.path,
        )

    return app
