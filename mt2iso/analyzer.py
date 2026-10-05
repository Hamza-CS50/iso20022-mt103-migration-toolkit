"""Data-loss / inference analyzer: what did the MT format force us to lose or guess?"""
from collections import Counter
from typing import List
from .models import Finding, WARNING, DATA_LOSS
from .mt103 import MT103
from .mapper import Conversion
from .validator import RULES, _f


def mt_level_findings(mt: MT103) -> List[Finding]:
    """Loss indicators visible only in the legacy message."""
    out = []
    if mt.fatal:
        return out
    v70 = mt.get("70")
    if v70:
        lines = v70.split("\n")
        if len(lines) == 4 and len(lines[3]) >= 30:
            out.append(_f(mt.msg_id, "DL_RMT_TRUNC_SUSPECT", ":70:", "All four 35-character lines are used; sender text was probably cut off at the MT limit"))
    return out


def lineage_mix(conv: Conversion) -> Counter:
    return Counter(l.method for l in conv.lineage)


def score(findings: List[Finding], rejected: bool) -> int:
    if rejected:
        return 0
    s = 100
    for f in findings:
        if f.severity == "ERROR":
            s -= 30
        elif f.severity == "WARNING":
            s -= 6
        elif f.category in ("INFERENCE", "DATA_LOSS"):
            s -= 2
    return max(0, s)


def status_of(findings: List[Finding], rejected: bool) -> str:
    if rejected:
        return "REJECTED"
    if any(f.severity == "ERROR" for f in findings):
        return "FAILED_VALIDATION"
    if any(f.severity == "WARNING" for f in findings):
        return "PASS_WITH_WARNINGS"
    return "PASS_CLEAN"
