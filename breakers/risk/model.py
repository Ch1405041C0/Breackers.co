from dataclasses import asdict, dataclass, field

@dataclass(frozen=True)
class Evidence:
    source_type: str
    reference: str
    excerpt: str = ""

@dataclass
class Risk:
    id: str
    area: str
    severity: str
    title: str
    hypothesis: str
    status: str = "identified"
    confidence: float = 0.5
    evidence: list[Evidence] = field(default_factory=list)
    missing_evidence: list[str] = field(default_factory=list)
    suggested_action: str = ""

    def to_dict(self) -> dict:
        return asdict(self)
