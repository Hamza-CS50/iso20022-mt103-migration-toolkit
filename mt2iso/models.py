"""Shared data structures."""
from dataclasses import dataclass, field
from typing import List, Optional, Dict

# Severities
ERROR, WARNING, INFO = "ERROR", "WARNING", "INFO"

# Categories
SYNTAX, SCHEMA, BUSINESS, ADDRESS, DATA_LOSS, INFERENCE, ENRICHMENT = (
    "SYNTAX", "SCHEMA", "BUSINESS", "ADDRESS", "DATA_LOSS", "INFERENCE", "ENRICHMENT")

# Lineage methods: how an ISO 20022 leaf element got its value
DIRECT, CODE, PARSED, INFERRED, FREETEXT = "DIRECT", "CODE", "PARSED", "INFERRED", "FREETEXT"


@dataclass
class Finding:
    msg_id: str
    rule_id: str
    category: str
    severity: str
    path: str
    message: str

    def as_row(self):
        return [self.msg_id, self.rule_id, self.category, self.severity, self.path, self.message]


@dataclass
class Lineage:
    path: str      # e.g. CdtTrfTxInf/Dbtr/PstlAdr/TwnNm
    source: str    # e.g. ":50K: line 3"
    method: str    # DIRECT | CODE | PARSED | INFERRED | FREETEXT

    @property
    def group(self) -> str:
        parts = self.path.split("/")
        if parts[0] == "GrpHdr":
            return "GrpHdr"
        return parts[1] if len(parts) > 1 else parts[0]


@dataclass
class Party:
    option: str                       # 'A','D','F','K',''  (field option letter)
    account: Optional[str] = None
    bic: Optional[str] = None
    name_lines: List[str] = field(default_factory=list)   # free-text lines (name then address)
    struct: Dict[str, List[str]] = field(default_factory=dict)  # for F option: {'1': [...], '2': [...], '3': [...]}
    clearing: Optional[str] = None
    raw: str = ""
