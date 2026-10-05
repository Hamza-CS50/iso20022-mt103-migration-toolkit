"""End-to-end batch pipeline: parse -> map -> validate -> analyze -> evaluate."""
import csv
import glob
import json
import os
from collections import Counter, defaultdict
from lxml import etree

from .mt103 import parse_mt103
from .mapper import convert
from .validator import validate_mt, validate_mx, RULES
from .analyzer import mt_level_findings, score, status_of

import datetime as dt
FIXED_NOW = dt.datetime(2026, 10, 3, 9, 0, 0, tzinfo=dt.timezone.utc)   # reproducible output


def process_text(msg_id, text, xsd_path=None, now=FIXED_NOW):
    mt = parse_mt103(text, msg_id)
    findings = validate_mt(mt)
    conv = convert(mt, now=now)
    rejected = conv.xml is None
    if not rejected:
        findings += validate_mx(msg_id, conv.xml, xsd_path)
        findings += conv.findings
        findings += mt_level_findings(mt)
    seen, uniq = set(), []                     # collapse exact duplicates (e.g. two parties, same rule)
    for f in findings:
        k = (f.rule_id, f.path, f.message)
        if k not in seen:
            seen.add(k); uniq.append(f)
    return mt, conv, uniq, rejected


def run(data_dir, out_dir, xsd_path=None):
    os.makedirs(os.path.join(out_dir, "pacs008"), exist_ok=True)
    manifest = {}
    with open(os.path.join(data_dir, "manifest.csv")) as f:
        for r in csv.DictReader(f):
            manifest[r["msg_id"]] = r
    results, all_findings, all_lineage = [], [], []
    for path in sorted(glob.glob(os.path.join(data_dir, "mt103", "*.txt"))):
        msg_id = os.path.splitext(os.path.basename(path))[0]
        with open(path) as fh:
            text = fh.read()
        mt, conv, findings, rejected = process_text(msg_id, text, xsd_path)
        if conv.xml:
            with open(os.path.join(out_dir, "pacs008", msg_id + ".xml"), "wb") as f:
                f.write(conv.xml)
        m = manifest.get(msg_id, {})
        sev = Counter(f.severity for f in findings)
        cat = Counter(f.category for f in findings)
        mix = Counter(l.method for l in conv.lineage)
        n_leaf = sum(mix.values())
        results.append(dict(
            msg_id=msg_id, scenario=m.get("scenario", ""), corridor=m.get("corridor", ""), currency=m.get("currency", ""),
            amount=float(m.get("amount") or 0), injected_defect=m.get("injected_defect", ""),
            status=status_of(findings, rejected), score=score(findings, rejected),
            errors=sev["ERROR"], warnings=sev["WARNING"], infos=sev["INFO"],
            inference=cat["INFERENCE"], data_loss=cat["DATA_LOSS"], enrichment=cat["ENRICHMENT"],
            leaf_elements=n_leaf, direct=mix["DIRECT"], code=mix["CODE"], parsed=mix["PARSED"],
            inferred=mix["INFERRED"], freetext=mix["FREETEXT"]))
        all_findings += findings
        all_lineage += [(msg_id, l.path, l.group, l.source, l.method) for l in conv.lineage]

    # ---- evaluation against injected ground truth
    by_msg = defaultdict(set)
    for f in all_findings:
        by_msg[f.msg_id].add(f.rule_id)
    evaluation = []
    for mid, m in manifest.items():
        if m["injected_defect"]:
            exp = m["expected_rule"]
            evaluation.append(dict(msg_id=mid, defect=m["injected_defect"], expected_rule=exp, detected=exp in by_msg[mid]))
    clean = [r for r in results if not r["injected_defect"]]
    false_alarms = [r["msg_id"] for r in clean if r["errors"] > 0]

    # ---- address structuring by role and country
    addr_rows = _address_stats(all_lineage, results)
    summary = _summary(results, all_findings, all_lineage, evaluation, false_alarms, addr_rows)

    _write_csv(os.path.join(out_dir, "results.csv"), results)
    _write_csv(os.path.join(out_dir, "findings.csv"), [dict(msg_id=f.msg_id, rule_id=f.rule_id, category=f.category, severity=f.severity, path=f.path, message=f.message) for f in all_findings])
    _write_csv(os.path.join(out_dir, "lineage.csv"), [dict(msg_id=a, path=b, group=c, source=d, method=e) for a, b, c, d, e in all_lineage])
    _write_csv(os.path.join(out_dir, "evaluation.csv"), evaluation)
    _write_csv(os.path.join(out_dir, "address.csv"), addr_rows)
    with open(os.path.join(out_dir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    return results, all_findings, all_lineage, evaluation, summary


def _address_stats(lineage, results):
    """Per party-role: has town AND country in output? plus street structured?"""
    roles = defaultdict(lambda: defaultdict(set))
    for mid, path, group, src, method in lineage:
        if "/PstlAdr/" in path and group in ("Dbtr", "Cdtr"):
            roles[(mid, group)][path.split("/")[-1]].add(method)
    corr = {r["msg_id"]: r["corridor"] for r in results}
    out = []
    for (mid, role), el in roles.items():
        country = corr[mid].split(">")[0 if role == "Dbtr" else 1]
        out.append(dict(msg_id=mid, role=role, country=country, town_ctry="TwnNm" in el and "Ctry" in el,
                        street="StrtNm" in el, adrline="AdrLine" in el))
    return out


def _summary(results, findings, lineage, evaluation, false_alarms, addr):
    n = len(results)
    st = Counter(r["status"] for r in results)
    rules = Counter(f.rule_id for f in findings)
    cats = Counter(f.category for f in findings)
    mix = Counter(l[4] for l in lineage)
    grp = defaultdict(Counter)
    for l in lineage:
        grp[l[2]][l[4]] += 1
    rec = defaultdict(lambda: [0, 0])
    for e in evaluation:
        rec[e["defect"]][0] += 1
        rec[e["defect"]][1] += int(e["detected"])
    by_country = defaultdict(lambda: [0, 0, 0])
    for a in addr:
        c = by_country[a["country"]]
        c[0] += 1; c[1] += int(a["town_ctry"]); c[2] += int(a["street"])
    by_scen = defaultdict(Counter)
    for r in results:
        by_scen[r["scenario"]][r["status"]] += 1
    stp = st["PASS_CLEAN"] + st["PASS_WITH_WARNINGS"]
    return dict(
        messages=n, status=dict(st), stp_rate=stp / n, repair_rate=(st["FAILED_VALIDATION"] + st["REJECTED"]) / n,
        avg_score=sum(r["score"] for r in results) / n,
        rules=dict(rules), categories=dict(cats), lineage_mix=dict(mix),
        lineage_by_group={k: dict(v) for k, v in grp.items()},
        deterministic_share=(mix["DIRECT"] + mix["CODE"]) / sum(mix.values()),
        heuristic_share=(mix["PARSED"]) / sum(mix.values()), inferred_share=mix["INFERRED"] / sum(mix.values()),
        freetext_share=mix["FREETEXT"] / sum(mix.values()),
        defects_injected=len(evaluation), defects_detected=sum(int(e["detected"]) for e in evaluation),
        recall_by_defect={k: dict(injected=v[0], detected=v[1]) for k, v in sorted(rec.items())},
        clean_messages=sum(1 for r in results if not r["injected_defect"]), false_alarm_messages=false_alarms,
        address_by_country={k: dict(parties=v[0], town_country=v[1], street=v[2]) for k, v in sorted(by_country.items())},
        status_by_scenario={k: dict(v) for k, v in sorted(by_scen.items())},
        address_parties=len(addr), address_town_country=sum(int(a["town_ctry"]) for a in addr),
        address_street=sum(int(a["street"]) for a in addr),
    )


def _write_csv(path, rows):
    if not rows:
        open(path, "w").close(); return
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
