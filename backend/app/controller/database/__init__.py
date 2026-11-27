from .common import blueprint
from . import charts, connections, tables, views  # Register routes on the shared blueprint.

__all__ = ["blueprint"]
