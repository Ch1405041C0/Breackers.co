from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Finding:
    engine: str
    severity: str
    title: str
    evidence: str = ""
    category: str = "quality"

    def to_dict(self) -> dict:
        return asdict(self)
