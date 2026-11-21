from eye.entity.health import HealthStatus


def get_health() -> HealthStatus:
    return HealthStatus(status="ok")
