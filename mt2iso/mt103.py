"""Parser for SWIFT FIN MT103 (single customer credit transfer)."""
import re
import datetime as dt
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from .models import Party

MANDATORY = [("20", ["20"]), ("23B", ["23B"]), ("32A", ["32A"]),
             ("50", ["50A", "50F", "50K"]), ("59", ["59", "59A", "59F"]), ("71A", ["71A"])]
BANK_OPCODES = {"CRED", "CRTS", "SPAY", "SPRI", "SSTD"}
CHARGES = {"OUR", "SHA", "BEN"}


@dataclass
class SyntaxIssue:
    rule: str
    field: str
    message: str
    fatal: bool = False


@dataclass
class MT103:
    msg_id: str
    raw: str
    sender_bic: Optional[str] = None
    receiver_bic: Optional[str] = None
    user_ref: Optional[str] = None
    uetr: Optional[str] = None
    fields: Dict[str, List[str]] = field(default_factory=dict)
    issues: List[SyntaxIssue] = field(default_factory=list)
    value_date: Optional[dt.date] = None
    ccy: Optional[str] = None
    amount: Optional[str] = None            # as written in MT, e.g. "1234,56"

    def get(self, tag: str) -> Optional[str]:
        v = self.fields.get(tag)
        return v[0] if v else None

    def all(self, tag: str) -> List[str]:
        return self.fields.get(tag, [])

    @property
    def fatal(self) -> bool:
        return any(i.fatal for i in self.issues)

    def first_tag(self, options: List[str]) -> Optional[str]:
        for o in options:
            if o in self.fields:
                return o
        return None


def split_blocks(text: str) -> Dict[str, str]:
    blocks, i, n = {}, 0, len(text)
    while i < n:
        m = re.match(r"\{(\d):", text[i:])
        if not m:
            i += 1
            continue
        j, depth = i + m.end(), 1
        while j < n and depth:
            depth += {"{": 1, "}": -1}.get(text[j], 0)
            j += 1
        blocks[m.group(1)] = text[i + m.end(): j - 1]
        i = j
    return blocks


def _bic11(lt: str) -> Optional[str]:
    lt = lt.strip()
    return (lt[:8] + lt[9:12]) if len(lt) >= 12 else None


_FIELD = re.compile(r"^:(\d{2}[A-Z]?):(.*)$")


def parse_mt103(text: str, msg_id: str) -> MT103:
    mt = MT103(msg_id=msg_id, raw=text)
    blocks = split_blocks(text)
    b1, b2, b3, b4 = (blocks.get(k) for k in "1234")
    if b1 and len(b1) >= 15:
        mt.sender_bic = _bic11(b1[3:15])
    if b2 and len(b2) >= 16:
        mt.receiver_bic = _bic11(b2[4:16])
    if b3:
        for tag, val in re.findall(r"\{(\d{3}):([^}]*)\}", b3):
            if tag == "121":
                mt.uetr = val.strip().lower()
            elif tag == "108":
                mt.user_ref = val.strip()
    if b4 is None:
        mt.issues.append(SyntaxIssue("SX_MISSING_FIELD", "block4", "Text block {4:} not found", True))
        return mt
    cur_tag, cur_idx = None, 0
    for line in b4.replace("\r", "").split("\n"):
        m = _FIELD.match(line)
        if m:
            cur_tag = m.group(1)
            mt.fields.setdefault(cur_tag, []).append(m.group(2))
            cur_idx = len(mt.fields[cur_tag]) - 1
        elif cur_tag is not None and line.strip() != "-":
            mt.fields[cur_tag][cur_idx] += "\n" + line
    _check(mt)
    return mt


def _check(mt: MT103) -> None:
    add = mt.issues.append
    for name, opts in MANDATORY:
        if not any(o in mt.fields for o in opts):
            add(SyntaxIssue("SX_MISSING_FIELD", name, f"Mandatory field :{name}: is missing", True))
    f20 = mt.get("20")
    if f20 is not None and (len(f20) > 16 or f20.startswith("/") or f20.endswith("/") or "//" in f20):
        add(SyntaxIssue("SX_FIELD_FORMAT", "20", "Sender's reference must be <=16 chars, no leading/trailing '/' or '//'"))
    f23 = mt.get("23B")
    if f23 is not None and f23.strip() not in BANK_OPCODES:
        add(SyntaxIssue("SX_CODE_INVALID", "23B", f"Bank operation code '{f23.strip()}' not valid"))
    f71 = mt.get("71A")
    if f71 is not None and f71.strip() not in CHARGES:
        add(SyntaxIssue("SX_CODE_INVALID", "71A", f"Details of charges '{f71.strip()}' not in OUR/SHA/BEN", True))
    f32 = mt.get("32A")
    if f32 is not None:
        m = re.match(r"^(\d{6})([A-Z]{3})(\d{1,15},\d{0,2}\d?)$", f32.strip())
        if not m:
            add(SyntaxIssue("SX_AMOUNT_FORMAT" if re.match(r"^\d{6}[A-Z]{3}", f32.strip()) else "SX_FIELD_FORMAT",
                            "32A", f"Field 32A '{f32.strip()}' malformed (YYMMDD + CCY + amount with decimal comma)", True))
        else:
            ymd, mt.ccy, mt.amount = m.group(1), m.group(2), m.group(3)
            try:
                mt.value_date = dt.date(2000 + int(ymd[:2]), int(ymd[2:4]), int(ymd[4:6]))
            except ValueError:
                add(SyntaxIssue("SX_DATE_INVALID", "32A", f"Value date {ymd} is not a real calendar date", True))
    f33 = mt.get("33B")
    if f33 is not None and not re.match(r"^[A-Z]{3}\d{1,15},\d{0,3}$", f33.strip()):
        add(SyntaxIssue("SX_AMOUNT_FORMAT", "33B", f"Field 33B '{f33.strip()}' malformed"))
    f36 = mt.get("36")
    if f36 is not None and not re.match(r"^\d{1,12},\d{0,}$", f36.strip()):
        add(SyntaxIssue("SX_AMOUNT_FORMAT", "36", f"Exchange rate '{f36.strip()}' malformed"))
    # Free-text line limits: 35 chars per line, 4 lines for 70 and 50K/59, 6 for 72
    for tag, maxlines in (("70", 4), ("72", 6)):
        v = mt.get(tag)
        if v is not None:
            lines = v.split("\n")
            if len(lines) > maxlines:
                add(SyntaxIssue("SX_FIELD_LINES", tag, f":{tag}: has {len(lines)} lines (max {maxlines})"))
            if any(len(l) > 35 for l in lines):
                add(SyntaxIssue("SX_LINE_LENGTH", tag, f":{tag}: has a line longer than 35 characters"))
    for tag in ("50K", "59"):
        v = mt.get(tag)
        if v is not None and any(len(l) > 35 for l in v.split("\n")):
            add(SyntaxIssue("SX_LINE_LENGTH", tag, f":{tag}: has a line longer than 35 characters"))


# ---------------- party parsing ----------------

def parse_party(tag: str, value: str) -> Party:
    option = tag[2:] if len(tag) > 2 else ""
    lines = value.split("\n")
    p = Party(option=option, raw=value)
    if option == "A":
        if lines and lines[0].startswith("/"):
            p.account, lines = lines[0][1:], lines[1:]
        p.bic = (lines[0].strip() if lines else None) or None
        return p
    if option == "F":
        if lines and not re.match(r"^[1-8]/", lines[0]):
            p.account = lines[0].lstrip("/") or None
            lines = lines[1:]
        for l in lines:
            m = re.match(r"^([1-8])/(.*)$", l)
            if m:
                p.struct.setdefault(m.group(1), []).append(m.group(2))
        return p
    # K / D / no option: optional /account, optional //clearing, then name + address lines
    if lines and lines[0].startswith("//"):
        p.clearing, lines = lines[0][2:], lines[1:]
    elif lines and lines[0].startswith("/"):
        p.account, lines = lines[0][1:], lines[1:]
    p.name_lines = [l for l in lines if l.strip()]
    return p
