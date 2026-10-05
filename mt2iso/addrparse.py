"""Heuristic parser: free-text MT address lines -> structured/hybrid ISO 20022 postal address.

Every value this module produces is a *guess* from text. The mapper records them as PARSED
(read from text) or INFERRED (not in the text at all, e.g. country deduced from a town name).
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional
from .refdata import COUNTRIES, COUNTRY_NAMES, GAZETTEER


@dataclass
class AddrResult:
    street: Optional[str] = None
    bldg: Optional[str] = None
    pstcd: Optional[str] = None
    town: Optional[str] = None
    subdiv: Optional[str] = None
    ctry: Optional[str] = None
    ctry_inferred: bool = False
    lines: List[str] = field(default_factory=list)   # leftovers -> AdrLine

    @property
    def structured_fields(self) -> int:
        return sum(1 for v in (self.street, self.bldg, self.pstcd, self.town, self.subdiv, self.ctry) if v)


_US = re.compile(r"^(?P<town>.+?)\s+(?P<st>[A-Z]{2})\s+(?P<pc>\d{5})(?:\s+(?P<cc>[A-Z]{2}))?$")
_UK = re.compile(r"^(?P<town>[A-Z][A-Z .'-]*?)\s+(?P<pc>[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2})(?:\s+(?P<cc>[A-Z]{2}))?$")
_PC_FIRST = re.compile(r"^(?P<pc>\d{4,6})\s+(?P<town>[A-Z][A-Z .'-]*?)(?:\s+(?P<cc>[A-Z]{2}))?$")
_TOWN_PC = re.compile(r"^(?P<town>[A-Z][A-Z .'-]*?)\s+(?P<pc>\d{4,6})(?:\s+(?P<cc>[A-Z]{2}))?$")
_TOWN_CC = re.compile(r"^(?P<town>[A-Z][A-Z .'-]*?)\s+(?P<cc>[A-Z]{2})$")
_STREET_NUM_FIRST = re.compile(r"^(?P<bn>\d+[A-Z]?(?:[-/]\d+)?)\s+(?P<st>\D.*)$")
_STREET_NUM_LAST = re.compile(r"^(?P<st>[^\d]+?)\s+(?P<bn>\d+[A-Z]?(?:[-/]\d+)?)$")


def _last_line(line: str, res: AddrResult) -> bool:
    """Try to read town/country/postcode from the last address line. True if a town was found."""
    s = line.strip().upper()
    if s in COUNTRY_NAMES:                       # line is just a country name
        res.ctry = COUNTRY_NAMES[s]
        return False                             # town must come from previous line
    for name, cc in sorted(COUNTRY_NAMES.items(), key=lambda kv: -len(kv[0])):
        if s.endswith(" " + name):               # "KARACHI PAKISTAN"
            res.ctry = cc
            s = s[: -(len(name) + 1)].strip()
            break
    for rx in (_US, _UK, _PC_FIRST, _TOWN_PC):
        m = rx.match(s)
        if m:
            d = m.groupdict()
            cc = d.get("cc")
            if cc and cc not in COUNTRIES:
                continue
            res.town = d["town"].strip()
            res.pstcd = d.get("pc")
            res.subdiv = d.get("st")
            if cc:
                res.ctry = cc
            return True
    m = _TOWN_CC.match(s)
    if m and m.group("cc") in COUNTRIES:
        res.town, res.ctry = m.group("town").strip(), m.group("cc")
        return True
    if s in GAZETTEER:                           # bare, known town
        res.town = s
        return True
    return False


def parse_address(lines: List[str]) -> AddrResult:
    res = AddrResult()
    lines = [l.strip() for l in lines if l and l.strip()]
    if not lines:
        return res
    rest = list(lines)
    last = rest[-1]
    found = _last_line(last, res)
    if found:
        rest.pop()
    elif res.ctry:                               # last line was only a country name
        rest.pop()
        if rest and _last_line(rest[-1], res):
            rest.pop()
        elif rest and rest[-1].upper() in GAZETTEER:
            res.town = rest.pop().upper()
    # Country inferred from gazetteer when the text never states it
    if res.town and not res.ctry and res.town.upper() in GAZETTEER:
        res.ctry = GAZETTEER[res.town.upper()]
        res.ctry_inferred = True
    # Street + building number from the first remaining line that matches a safe pattern
    for i, l in enumerate(list(rest)):
        m = _STREET_NUM_FIRST.match(l.upper()) or _STREET_NUM_LAST.match(l.upper())
        if m and not res.street:
            res.street, res.bldg = m.group("st").strip(), m.group("bn")
            rest.pop(i)
            break
    res.lines = rest
    return res
