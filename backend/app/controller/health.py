from flask import Blueprint

from app.service.health import get_health
from app.util.response import ok

blueprint = Blueprint("health", __name__, url_prefix="/api")


@blueprint.get("/health")
def health():
    return ok(get_health().to_dict())
