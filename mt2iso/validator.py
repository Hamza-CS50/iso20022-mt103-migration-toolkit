"""Validation: (1) XSD schema, (2) MT-level network rules, (3) ISO 20022 business rules."""
import datetime as dt
import os
import re
from typing import List, Optional
from lxml import etree

from .models import (Finding, ERROR, WARNING, INFO, SCHEMA, BUSINESS, ADDRESS, SYNTAX)
from .mt103 import MT103
from .ibanutil import BIC_RE, iban_mod97_ok, iban_length_ok
from .refdata import COUNTRIES, CURRENCIES
from decimal import Decimal

NS = {"p": "urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08"}
DEFAULT_XSD = os.path.join(os.path.dirname(__file__), "..", "schemas", "pacs.008.001.08.subset.xsd")
_schema_cache = {}

# Rule catalogue: rule_id -> (category, severity, description)
RULES = {
    "SX_MISSING_FIELD":   ("SYNTAX", ERROR, "Mandatory MT103 field missing - message cannot be translated"),
    "SX_DATE_INVALID":    ("SYNTAX", ERROR, "Value date in :32A: is not a real calendar date"),
    "SX_AMOUNT_FORMAT":   ("SYNTAX", ERROR, "Amount not in SWIFT format (digits with a decimal comma)"),
    "SX_FIELD_FORMAT":    ("SYNTAX", ERROR, "Field does not match its FIN format definition"),
    "SX_CODE_INVALID":    ("SYNTAX", ERROR, "Code word not in the allowed list for the field"),
    "SX_LINE_LENGTH":     ("SYNTAX", ERROR, "Free-text line exceeds the 35-character FIN limit"),
    "SX_FIELD_LINES":     ("SYNTAX", ERROR, "Too many lines for the field"),
    "XSD_001":            ("SCHEMA", ERROR, "Output violates the pacs.008 XSD (structure, order, type facet)"),
    "BR_BIC_FMT":         ("BUSINESS", ERROR, "BIC does not match the 8/11-character BIC pattern"),
    "BR_BIC_CTRY":        ("BUSINESS", ERROR, "BIC characters 5-6 are not a valid ISO 3166 country"),
    "BR_IBAN_CHK":        ("BUSINESS", ERROR, "IBAN fails the ISO 13616 mod-97 check"),
    "BR_IBAN_LEN":        ("BUSINESS", ERROR, "IBAN length differs from the registry length for its country"),
    "BR_CCY_UNKNOWN":     ("BUSINESS", ERROR, "Currency code is not an ISO 4217 code known to the toolkit"),
    "BR_AMT_DECIMALS":    ("BUSINESS", ERROR, "Amount has more decimals than the currency allows"),
    "BR_AMT_POS":         ("BUSINESS", ERROR, "Amount must be greater than zero"),
    "BR_NAME_REQ":        ("BUSINESS", ERROR, "Debtor/creditor name missing"),
    "BR_ADDR_TWN_CTRY":   ("ADDRESS", ERROR, "Postal address lacks town and/or country - NAK risk from 14 Nov 2026 (CBPR+ SR2026)"),
    "BR_ADDR_LINES":      ("ADDRESS", WARNING, "Hybrid address allows at most 2 unstructured AdrLine elements"),
    "BR_ADDR_NONE":       ("ADDRESS", INFO, "No postal address supplied for party"),
    "BR_CHRG_RULE":       ("BUSINESS", ERROR, "Charge fields inconsistent with :71A: (OUR/SHA/BEN network rules)"),
    "BR_FX_RATE_MISSING": ("BUSINESS", WARNING, "Instructed currency differs from settlement currency but no exchange rate"),
    "BR_VALUE_DATE_WEEKEND": ("BUSINESS", WARNING, "Interbank settlement date falls on a Saturday or Sunday"),
    "BR_IBAN_ADDR_MISMATCH": ("BUSINESS", WARNING, "Account IBAN country differs from party address country (screening relevant)"),
    "BR_NON_IBAN_ACCT":   ("BUSINESS", WARNING, "Pakistani creditor account is not an IBAN; Raast onward credit needs an IBAN"),
    "BR_RMT_MULTI_USTRD": ("BUSINESS", WARNING, "Remittance info needed more than one Ustrd (CBPR+ allows one, max 140 chars)"),
    "BR_E2E_NOTPROVIDED": ("BUSINESS", INFO, "EndToEndId is NOTPROVIDED - originator reference not available"),
    "DL_NAME_TRUNC_SUSPECT": ("DATA_LOSS", WARNING, "Name fills the full 35-character MT line - probably truncated upstream"),
    "DL_RMT_TRUNC_SUSPECT":  ("DATA_LOSS", WARNING, "Remittance info uses all 4 MT lines nearly full - probably truncated upstream"),
    "DL_UNMAPPED_50F_LINES": ("DATA_LOSS", WARNING, "50F lines 4/-8/ (birth data, IDs) not carried to ISO 20022"),
    "INF_UETR_GENERATED":    ("INFERENCE", WARNING, "No UETR in MT103; translator generated one (end-to-end tracking broken)"),
    "INF_DBTRAGT_INFERRED":  ("INFERENCE", INFO, "Debtor agent assumed from the sending bank (no :52a:)"),
    "INF_CDTRAGT_INFERRED":  ("INFERENCE", INFO, "Creditor agent assumed from the receiving bank (no :57a:)"),
    "INF_CHRG_AGENT_INFERRED": ("INFERENCE", INFO, "Charging agent assumed (MT :71F:/:71G: do not name it)"),
    "INF_CTRY_FROM_TOWN":    ("INFERENCE", WARNING, "Country deduced from a town name rather than stated"),
    "GAIN_STRUCT_ADDR":      ("ENRICHMENT", INFO, "Free-text address turned into structured town/country elements"),
    "GAIN_STRUCT_RMT":       ("ENRICHMENT", INFO, "Code-word remittance data turned into structured Strd elements"),
}


def _schema(path: Optional[str]):
    path = os.path.abspath(path or DEFAULT_XSD)
    if path not in _schema_cache:
        _schema_cache[path] = etree.XMLSchema(etree.parse(path))
    return _schema_cache[path]


def _f(msg_id, rule, path, message):
    cat, sev, _ = RULES[rule]
    return Finding(msg_id, rule, cat, sev, path, message)


# ---------------------------------------------------------------- MT level
def validate_mt(mt: MT103) -> List[Finding]:
    out = []
    for i in mt.issues:
        out.append(_f(mt.msg_id, i.rule, f":{i.field}:", i.message))
    if mt.fatal:
        return out
    charge = mt.get("71A").strip() if mt.get("71A") else None
    has_f, has_g = bool(mt.all("71F")), bool(mt.all("71G"))
    if charge == "OUR" and has_f:
        out.append(_f(mt.msg_id, "BR_CHRG_RULE", ":71A:/:71F:", "With 71A=OUR, field 71F (sender's charges) is not allowed"))
    if charge == "BEN" and not has_f:
        out.append(_f(mt.msg_id, "BR_CHRG_RULE", ":71A:/:71F:", "With 71A=BEN at least one 71F is required"))
    if charge in ("BEN", "SHA") and has_g:
        out.append(_f(mt.msg_id, "BR_CHRG_RULE", ":71A:/:71G:", f"With 71A={charge}, field 71G is not allowed"))
    f33 = mt.get("33B")
    if f33 and re.match(r"^[A-Z]{3}", f33.strip()) and f33.strip()[:3] != mt.ccy and not mt.get("36"):
        out.append(_f(mt.msg_id, "BR_FX_RATE_MISSING", ":33B:/:36:", "33B currency differs from 32A currency but :36: exchange rate is absent"))
    return out


# ---------------------------------------------------------------- MX level
def validate_mx(msg_id: str, xml: bytes, xsd_path: Optional[str] = None) -> List[Finding]:
    out: List[Finding] = []
    doc = etree.fromstring(xml)
    schema = _schema(xsd_path)
    if not schema.validate(doc):
        for e in schema.error_log:
            out.append(_f(msg_id, "XSD_001", e.path or "", e.message.replace("{%s}" % NS["p"], "")))
    X = lambda node, q: node.xpath(q, namespaces=NS)

    # BICs
    for bic in X(doc, "//p:BICFI|//p:AnyBIC"):
        v = bic.text or ""
        if not BIC_RE.match(v):
            out.append(_f(msg_id, "BR_BIC_FMT", doc.getroottree().getpath(bic), f"'{v}' is not a valid BIC"))
        elif v[4:6] not in COUNTRIES:
            out.append(_f(msg_id, "BR_BIC_CTRY", doc.getroottree().getpath(bic), f"BIC '{v}' has invalid country code '{v[4:6]}'"))

    # IBANs
    for ib in X(doc, "//p:IBAN"):
        v = ib.text or ""
        path = doc.getroottree().getpath(ib)
        if iban_length_ok(v) is False:
            out.append(_f(msg_id, "BR_IBAN_LEN", path, f"IBAN '{v}' has {len(v)} chars; {v[:2]} IBANs must have a fixed registry length"))
        if not iban_mod97_ok(v):
            out.append(_f(msg_id, "BR_IBAN_CHK", path, f"IBAN '{v}' fails the mod-97 check digit test"))

    # Amounts and currencies
    for amt in X(doc, "//p:IntrBkSttlmAmt|//p:InstdAmt|//p:ChrgsInf/p:Amt"):
        ccy, txt = amt.get("Ccy"), (amt.text or "").strip()
        path = doc.getroottree().getpath(amt)
        if ccy not in CURRENCIES:
            out.append(_f(msg_id, "BR_CCY_UNKNOWN", path, f"Currency '{ccy}' is not a recognised ISO 4217 code"))
        else:
            try:
                d = Decimal(txt)
                if -d.as_tuple().exponent > CURRENCIES[ccy]:
                    out.append(_f(msg_id, "BR_AMT_DECIMALS", path, f"{ccy} allows {CURRENCIES[ccy]} decimals but amount is {txt}"))
                if d <= 0:
                    out.append(_f(msg_id, "BR_AMT_POS", path, "Amount must be > 0"))
            except Exception:
                pass

    # Settlement date on weekend
    for d in X(doc, "//p:IntrBkSttlmDt"):
        try:
            if dt.date.fromisoformat(d.text).weekday() >= 5:
                out.append(_f(msg_id, "BR_VALUE_DATE_WEEKEND", doc.getroottree().getpath(d), f"{d.text} is a weekend day"))
        except Exception:
            pass

    # Parties: name + address readiness
    for role in ("Dbtr", "Cdtr"):
        for p in X(doc, f"//p:CdtTrfTxInf/p:{role}"):
            path = f"CdtTrfTxInf/{role}"
            has_name = bool(X(p, "p:Nm"))
            if not has_name and not X(p, "p:Id"):
                out.append(_f(msg_id, "BR_NAME_REQ", path, f"{role} has no name"))
            elif not has_name:
                out.append(_f(msg_id, "BR_NAME_REQ", path, f"{role} identified by BIC only - name required for sanctions screening"))
            adr = X(p, "p:PstlAdr")
            if not adr:
                out.append(_f(msg_id, "BR_ADDR_NONE", path + "/PstlAdr", f"{role} has no postal address"))
            else:
                a = adr[0]
                miss = [n for n, q in (("TwnNm", "p:TwnNm"), ("Ctry", "p:Ctry")) if not X(a, q)]
                if miss:
                    out.append(_f(msg_id, "BR_ADDR_TWN_CTRY", path + "/PstlAdr", f"{role} address lacks {' and '.join(miss)}; unstructured addresses are rejected by CBPR+ from 14 Nov 2026"))
                if len(X(a, "p:AdrLine")) > 2:
                    out.append(_f(msg_id, "BR_ADDR_LINES", path + "/PstlAdr", f"{role} address has {len(X(a, 'p:AdrLine'))} AdrLine elements (max 2 in hybrid format)"))

    # IBAN country vs address country, and Pakistani non-IBAN creditor accounts
    for role, acct in (("Dbtr", "DbtrAcct"), ("Cdtr", "CdtrAcct")):
        for p in X(doc, f"//p:CdtTrfTxInf/p:{role}"):
            ctry = X(p, "p:PstlAdr/p:Ctry")
            ctry = ctry[0].text if ctry else None
            ibn = X(doc, f"//p:CdtTrfTxInf/p:{acct}/p:Id/p:IBAN")
            if ibn and ctry and ibn[0].text[:2] != ctry:
                out.append(_f(msg_id, "BR_IBAN_ADDR_MISMATCH", f"CdtTrfTxInf/{acct}",
                              f"{role} IBAN country {ibn[0].text[:2]} differs from address country {ctry}"))
    cd_agent = X(doc, "//p:CdtTrfTxInf/p:CdtrAgt/p:FinInstnId/p:BICFI")
    cd_ctry = X(doc, "//p:CdtTrfTxInf/p:Cdtr/p:PstlAdr/p:Ctry")
    pk_cred = (cd_agent and (cd_agent[0].text or "")[4:6] == "PK") or (cd_ctry and cd_ctry[0].text == "PK")
    if pk_cred and X(doc, "//p:CdtTrfTxInf/p:CdtrAcct/p:Id/p:Othr"):
        out.append(_f(msg_id, "BR_NON_IBAN_ACCT", "CdtTrfTxInf/CdtrAcct", "Creditor account in Pakistan is a local account number, not an IBAN"))

    if len(X(doc, "//p:RmtInf/p:Ustrd")) > 1:
        out.append(_f(msg_id, "BR_RMT_MULTI_USTRD", "CdtTrfTxInf/RmtInf", "Remittance text exceeded 140 characters and was split over several Ustrd"))
    if X(doc, "//p:EndToEndId[text()='NOTPROVIDED']"):
        out.append(_f(msg_id, "BR_E2E_NOTPROVIDED", "CdtTrfTxInf/PmtId/EndToEndId", "No /ROC/ originator reference in :70:"))
    return out
