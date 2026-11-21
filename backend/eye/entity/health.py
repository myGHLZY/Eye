from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class HealthStatus:
    status: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)
