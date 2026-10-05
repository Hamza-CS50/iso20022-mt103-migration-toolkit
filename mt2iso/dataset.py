"""Synthetic MT103 dataset generator with ground-truth defect labels.

100 fully fictional payments modelled on Pakistan-centred corridors (inbound workers'
remittances, inbound/outbound trade, services). 46 messages carry exactly one injected defect;
the manifest records which rule SHOULD fire, so detection recall can be measured.
All names, accounts and BICs are invented; any resemblance to real parties is coincidental.
"""
import csv
import datetime as dt
import hashlib
import os
import random
import uuid
from decimal import Decimal

from .ibanutil import make_iban

SEED = 20261003

BANKS = {   # fictional institutions; BIC format is valid, institutions are not real
    "PK": ["KRDBPKKA", "LHRNPKLA", "ISBTPKKA", "PSHRPKKA", "MLTNPKKA"],
    "AE": ["GLFBAEAD", "EMRTAEAA"], "SA": ["RYDHSARI", "JDDHSAJE"], "GB": ["LNDNGB2L", "MNCHGB2M"],
    "US": ["NYCBUS33", "HSTNUS44"], "DE": ["FRNKDEFF", "BRLNDEBB"], "CN": ["SHNGCNSH", "SZHNCNBK"],
    "SG": ["SNGPSGSG", "SGCMSGSG"],
}
CORRESPONDENTS = ["CORPUS33", "CRSPGB2L", "TRNSDEFF"]

PK_PERSONS = ["MUHAMMAD ALI KHAN", "AYESHA SIDDIQUI", "HASSAN RAZA", "FATIMA NOOR", "BILAL AHMED", "SANA MALIK",
              "USMAN TARIQ", "ZAINAB HUSSAIN", "IMRAN SHEIKH", "MARIAM QURESHI", "OMAR FAROOQ", "HINA BUTT"]
ABROAD_PERSONS = ["TARIQ MAHMOOD", "SAJID HUSSAIN", "NADEEM AKHTAR", "KASHIF JAVED", "RIZWAN ASLAM", "ADEEL SHAHZAD",
                  "JOHN SMITH", "MARIA GARCIA", "AHMED RAZA", "IQBAL HUSSAIN"]
PK_COMPANIES = ["KARACHI TEXTILE EXPORTS LTD", "LAHORE AGRO TRADERS", "INDUS SURGICAL WORKS", "PAKISTAN PACKAGING CO",
                "SIALKOT SPORTS GOODS LTD", "FAISALABAD FABRICS PVT LTD", "MARGALLA SOFTWARE HOUSE", "KOHSAR ELECTRONICS TRADING"]
FOREIGN_COMPANIES = {
    "CN": ["SHENZHEN COMPONENTS CO LTD", "SHANGHAI CHEMICALS LTD"], "DE": ["HAMBURG MASCHINEN GMBH", "BERLIN INSTRUMENTE AG"],
    "AE": ["GULF LOGISTICS FZE", "DUBAI TRADING LLC"], "SG": ["SINGAPORE COMMODITIES PTE LTD"],
    "US": ["TEXAS MACHINERY INC"], "GB": ["MANCHESTER FABRICS LTD"],
}
LONG_NAMES = ["KARACHI INTERNATIONAL TRADING COMPANY LIMITED", "LAHORE INDUSTRIAL MACHINERY AND SPARES PVT LTD",
              "ISLAMABAD ADVANCED TECHNOLOGY SOLUTIONS LIMITED"]
PURPOSES = ["FAMILY SUPPORT", "HOUSE RENT", "SCHOOL FEES", "MEDICAL EXPENSES", "GIFT", "SAVINGS"]
GOODS = ["COTTON YARN", "SURGICAL INSTRUMENTS", "ELECTRONIC COMPONENTS", "PACKAGING MATERIAL", "SOFTWARE SERVICES", "SPORTS GOODS"]
UNKNOWN_TOWNS = {"PK": ["WAZIRABAD", "MIRPUR KHAS", "GUJRANWALA"], "AE": ["AJMAN", "FUJAIRAH"], "SA": ["KHOBAR", "TABUK"],
                 "GB": ["BRADFORD", "LEEDS"], "US": ["AUSTIN TX"], "DE": ["BREMEN"], "CN": ["CHENGDU"], "SG": ["JURONG"]}
FX_RATES = {("USD", "EUR"): "0,9215", ("USD", "CNY"): "7,1480", ("USD", "GBP"): "0,7840", ("EUR", "USD"): "1,0850"}


def _addr(rng, cc, town_variant=True):
    """Return (address_lines, town) for country cc in a realistic MT style."""
    n, m, k = rng.randint(1, 240), rng.randint(1, 30), rng.randint(1, 9)
    if cc == "PK":
        town = rng.choice(["KARACHI", "LAHORE", "ISLAMABAD", "RAWALPINDI", "FAISALABAD", "SIALKOT"])
        street = rng.choice([f"HOUSE {n} STREET {m} DHA PHASE {k}", f"PLOT {n} BLOCK {k} CLIFTON", f"FLAT {n} GULSHAN-E-IQBAL BLOCK {m}",
                             f"{n} MALL ROAD", f"OFFICE {n} I.I. CHUNDRIGAR ROAD"])
        pc = str(rng.randint(40000, 75999))
        last = rng.choices([f"{town} PK", f"{town} {pc} PK", f"{pc} {town} PK", f"{town} PAKISTAN"], [55, 20, 15, 10])[0]
    elif cc == "AE":
        town = rng.choice(["DUBAI", "ABU DHABI", "SHARJAH"])
        street = rng.choice([f"{n} SHEIKH ZAYED ROAD", f"OFFICE {n} AL WASL TOWER", f"VILLA {n} AL BARSHA"])
        last = rng.choices([f"{town} AE", f"{town} UNITED ARAB EMIRATES"], [80, 20])[0]
    elif cc == "SA":
        town = rng.choice(["RIYADH", "JEDDAH", "DAMMAM"])
        street = rng.choice([f"{n} KING FAHD ROAD", f"BUILDING {n} OLAYA STREET"])
        last = rng.choices([f"{town} SA", f"{town} {rng.randint(11000, 12999)} SA"], [70, 30])[0]
    elif cc == "GB":
        town = rng.choice(["LONDON", "MANCHESTER", "BIRMINGHAM"])
        street = rng.choice([f"{n} HIGH STREET", f"FLAT {m} {n} BAKER STREET"])
        pc = rng.choice(["E1 6AN", "M1 4BT", "B1 1AA", "N7 8PQ"])
        last = f"{town} {pc} GB"
    elif cc == "US":
        town, st = rng.choice([("NEW YORK", "NY"), ("HOUSTON", "TX"), ("CHICAGO", "IL")])
        street = rng.choice([f"{n} MAIN STREET", f"{n} BROADWAY"])
        last = f"{town} {st} {rng.randint(10001, 77999)} US"
    elif cc == "DE":
        town = rng.choice(["FRANKFURT", "BERLIN", "MUNICH", "HAMBURG"])
        street = rng.choice([f"HAUPTSTRASSE {n}", f"BAHNHOFSTRASSE {m}"])
        last = f"{rng.randint(10115, 80999)} {town} DE"
    elif cc == "CN":
        town = rng.choice(["SHENZHEN", "SHANGHAI", "GUANGZHOU"])
        street = rng.choice([f"NO {n} ZHONGSHAN ROAD", f"{n} NANSHAN ROAD"])
        last = rng.choices([f"{town} CN", f"{town} {rng.randint(200000, 518999)} CN"], [70, 30])[0]
    else:  # SG
        town = "SINGAPORE"
        street = f"{n} ROBINSON ROAD"
        last = f"SINGAPORE {rng.randint(60000, 99999)} SG"
    return [street, last], town


def _account(rng, cc):
    digits = lambda x: "".join(str(rng.randint(0, 9)) for _ in range(x))
    letters = lambda x: "".join(rng.choice("ABCDEFGHJKLMNPRSTUVWXYZ") for _ in range(x))
    if cc == "PK": return make_iban("PK", letters(4) + digits(16))
    if cc == "AE": return make_iban("AE", digits(3) + digits(16))
    if cc == "SA": return make_iban("SA", digits(2) + digits(18))
    if cc == "GB": return make_iban("GB", letters(4) + digits(14))
    if cc == "DE": return make_iban("DE", digits(18))
    return digits(rng.choice([10, 12]))     # US, CN, SG: local numbers, no IBAN


def _party(rng, cc, kind, structured=False):
    if kind == "person":
        name = rng.choice(PK_PERSONS if cc == "PK" else ABROAD_PERSONS)
    else:
        name = rng.choice(PK_COMPANIES if cc == "PK" else FOREIGN_COMPANIES.get(cc, FOREIGN_COMPANIES["AE"]))
    lines, town = _addr(rng, cc)
    return {"cc": cc, "name": name, "addr": lines, "acct": _account(rng, cc), "opt": "F" if structured else "K", "town": town}


def _next_weekday(rng):
    d = dt.date(2026, 9, 14) + dt.timedelta(days=rng.randint(0, 39))
    while d.weekday() >= 5:
        d += dt.timedelta(days=1)
    return d


def _bic(rng, cc):
    return rng.choice(BANKS[cc]) + "XXX"


def build_spec(rng, i, scenario):
    sid = f"MSG{i:03d}"
    feats = []
    if scenario == "S1":
        scc = rng.choices(["AE", "SA", "GB", "US"], [35, 25, 20, 20])[0]
        ccy = {"AE": rng.choice(["AED", "AED", "USD"]), "SA": "SAR", "GB": "GBP", "US": "USD"}[scc]
        dbtr, cdtr, inbound = _party(rng, scc, "person"), _party(rng, "PK", "person"), True
        amount = Decimal(rng.randint(15000, 600000)) / 100
    elif scenario == "S2":
        scc = rng.choice(["CN", "DE", "SG", "US", "AE", "GB"])
        ccy = {"DE": "EUR", "CN": rng.choice(["USD", "CNY"])}.get(scc, "USD")
        dbtr, cdtr, inbound = _party(rng, scc, "company"), _party(rng, "PK", "company"), True
        amount = Decimal(rng.randint(500000, 25000000)) / 100
    elif scenario == "S3":
        scc = rng.choice(["CN", "DE", "AE", "SG"])
        ccy = {"DE": "EUR", "CN": rng.choice(["USD", "CNY"])}.get(scc, "USD")
        dbtr = _party(rng, "PK", "company", structured=rng.random() < 0.3)
        cdtr, inbound = _party(rng, scc, "company"), False
        amount = Decimal(rng.randint(500000, 25000000)) / 100
    else:  # S4 services, both directions
        scc = rng.choice(["GB", "US"])
        ccy = "GBP" if scc == "GB" else "USD"
        inbound = rng.random() < 0.5
        dbtr, cdtr = (_party(rng, scc, "company"), _party(rng, "PK", "company")) if inbound else (_party(rng, "PK", "company"), _party(rng, scc, "company"))
        amount = Decimal(rng.randint(100000, 4000000)) / 100
    if cdtr["opt"] == "K" and rng.random() < 0.12 and scenario != "S1":
        cdtr["opt"] = "F"
    for p in (dbtr, cdtr):
        if p["opt"] == "F": feats.append("structured_" + ("50F" if p is dbtr else "59F"))
    sender = _bic(rng, dbtr["cc"])
    receiver = _bic(rng, cdtr["cc"])
    spec = dict(id=sid, scenario=scenario, corridor=f"{dbtr['cc']}>{cdtr['cc']}", sender=sender, receiver=receiver, date=_next_weekday(rng),
                ccy=ccy, amount=amount, dbtr=dbtr, cdtr=cdtr, f23b=rng.choice(["CRED"] * 6 + ["SPRI", "SSTD"]),
                f20=f"{'PK' if not inbound else 'FX'}{scenario}{rng.randint(10**7, 10**8 - 1)}", uetr=None, f33b=None, f36=None,
                f52a=None, f56a=None, f57a=None, f53a=None, f54a=None, f70=None, f71a="SHA", f71f=[], f71g=[], f72=[], f77b=[], feats=feats, defects=[], inbound=inbound)
    if rng.random() < 0.75:
        spec["uetr"] = str(uuid.UUID(bytes=hashlib.md5(f"u{sid}".encode()).digest(), version=4))
    else:
        feats.append("no_uetr")
    if rng.random() < 0.60: spec["f52a"] = sender
    else: feats.append("no_52a")
    if rng.random() < 0.30:
        other = rng.choice([b for b in BANKS[cdtr["cc"]] if b + "XXX" != receiver] or BANKS[cdtr["cc"]]) + "XXX"
        spec["f57a"] = other
    else: feats.append("no_57a")
    if rng.random() < 0.15: spec["f56a"] = rng.choice(CORRESPONDENTS) + "XXX"; feats.append("intermediary_56A")
    if rng.random() < 0.08: spec["f53a"] = rng.choice(CORRESPONDENTS) + "XXX"; feats.append("reimb_53A")
    # remittance information
    if scenario == "S1":
        if rng.random() < 0.30: spec["f70"] = [f"/RFB/{rng.randint(100000, 999999)}", rng.choice(PURPOSES)]; feats.append("RFB")
        else: spec["f70"] = [rng.choice(PURPOSES)]
    else:
        inv = f"INV-2026-{rng.randint(1000, 9999)}"
        r = rng.random()
        if r < 0.65: spec["f70"] = [f"/INV/{inv}", f"PAYMENT FOR {rng.choice(GOODS)}"]; feats.append("INV")
        else: spec["f70"] = [f"PAYMENT FOR {rng.choice(GOODS)}", f"CONTRACT {rng.randint(100, 999)}/2026"]
        if rng.random() < 0.20: spec["f70"].insert(0, f"/ROC/ORD{rng.randint(10**6, 10**7 - 1)}"); feats.append("ROC")
    # charges
    r = rng.random()
    if r < 0.60: spec["f71a"] = "SHA"
    elif r < 0.85:
        spec["f71a"] = "OUR"
        if rng.random() < 0.4: spec["f71g"] = [f"{ccy}{rng.randint(5, 40)},00"]; feats.append("charges_71G")
    else:
        spec["f71a"] = "BEN"; spec["f71f"] = [f"{ccy}{rng.randint(5, 40)},00"]; feats.append("charges_71F")
    # FX
    if scenario in ("S2", "S3") and rng.random() < 0.35:
        for (a, b), rate in FX_RATES.items():
            if a == ccy:
                spec["f33b"] = (b, (amount * Decimal(rate.replace(",", "."))).quantize(Decimal("0.01")))
                spec["f36"] = rate; feats.append("FX_33B_36"); break
    if rng.random() < 0.15: spec["f72"] = ["/INS/" + (spec["f57a"] or receiver)[:8], "/ACC/CREDIT BENEFICIARY ACCOUNT"]; feats.append("narrative_72")
    if "PK" in (dbtr["cc"], cdtr["cc"]) and rng.random() < 0.20: spec["f77b"] = [f"/{'BENEFRES' if inbound else 'ORDERRES'}/PK//"]; feats.append("reg_77B")
    return spec


def _party_lines(tag, p):
    if p["opt"] == "F":
        out = [f":{tag}F:/{p['acct']}", f"1/{p['name']}", f"2/{p['addr'][0]}"]
        out.append(f"3/{p['cc']}/{p['town']}")
        return out
    first = f":{tag}K:" if tag == "50" else ":59:"
    return [first + f"/{p['acct']}", p["name"]] + p["addr"]


def render(s):
    b3 = "{3:" + "".join(["{108:" + s["id"] + "}"] + (["{121:" + s["uetr"] + "}"] if s["uetr"] else [])) + "}"
    L = [f"{{1:F01{s['sender'][:8]}AXXX0000000000}}{{2:I103{s['receiver'][:8]}AXXXN}}{b3}{{4:"]
    d = s["date"]
    if s.get("raw_date"): ymd = s["raw_date"]
    else: ymd = d.strftime("%y%m%d")
    amt = s["amount_text"] if s.get("amount_text") else f"{s['amount']:.2f}".replace(".", ",")
    if "20" not in s.get("drop", []): L.append(f":20:{s['f20']}")
    L.append(f":23B:{s['f23b']}")
    L.append(f":32A:{ymd}{s['ccy']}{amt}")
    if s["f33b"]: L.append(f":33B:{s['f33b'][0]}{str(s['f33b'][1]).replace('.', ',')}")
    if s["f36"]: L.append(f":36:{s['f36']}")
    L += _party_lines("50", s["dbtr"])
    if s["f52a"]: L.append(f":52A:{s['f52a']}")
    if s["f53a"]: L.append(f":53A:{s['f53a']}")
    if s["f56a"]: L.append(f":56A:{s['f56a']}")
    if s["f57a"]: L.append(f":57A:{s['f57a']}")
    if "59" not in s.get("drop", []):
        L += _party_lines("59", s["cdtr"])
    if s["f70"]: L.append(":70:" + "\n".join(s["f70"]))
    if "71A" not in s.get("drop", []): L.append(f":71A:{s['f71a']}")
    for v in s["f71f"]: L.append(f":71F:{v}")
    for v in s["f71g"]: L.append(f":71G:{v}")
    if s["f72"]: L.append(":72:" + "\n".join(s["f72"]))
    if s["f77b"]: L.append(":77B:" + "\n".join(s["f77b"]))
    L.append("-}")
    return "\n".join(L)


# -------------------------------------------------------------------- defects
def _bump_iban(iban):             # corrupt check digits
    cd = (int(iban[2:4]) % 97) + 1
    return iban[:2] + f"{cd:02d}" + iban[4:]


def _iban_party(s):
    for k in ("cdtr", "dbtr"):
        if len(s[k]["acct"]) > 12 and s[k]["acct"][:2] in ("PK", "AE", "SA", "GB", "DE"):
            return s[k]
    return None


def _d01(s, rng): p = _iban_party(s); p["acct"] = _bump_iban(p["acct"]); return "BR_IBAN_CHK"
def _d02(s, rng): p = _iban_party(s); p["acct"] = p["acct"] + str(rng.randint(0, 9)); return "BR_IBAN_LEN"
def _d03(s, rng):
    v = rng.choice([("KRDBPKK", "BR_BIC_FMT"), ("KRDBPKKAXX", "BR_BIC_FMT"), ("KRDBXXKAXXX", "BR_BIC_CTRY")])
    s["f57a"] = v[0]; return v[1]
def _d06(s, rng):
    p = rng.choice([s["cdtr"], s["dbtr"]])
    p["addr"] = p["addr"][:-1] + [rng.choice(UNKNOWN_TOWNS[p["cc"]])]; return "BR_ADDR_TWN_CTRY"
def _d07(s, rng):
    p = rng.choice([s["cdtr"], s["dbtr"]])
    if p["cc"] in ("US", "GB", "DE", "CN", "SG"): p = s["cdtr"] if p is s["dbtr"] else s["dbtr"]
    p["addr"] = p["addr"][:-1] + [p["town"]]; return "INF_CTRY_FROM_TOWN"
def _d08(s, rng):
    p = s["cdtr"] if s["cdtr"]["opt"] == "K" else s["dbtr"]
    p["name"] = rng.choice(LONG_NAMES)[:35]; p["opt"] = "K"; return "DL_NAME_TRUNC_SUSPECT"
def _d09(s, rng):   # four MT lines, every one (almost) full: the classic 4x35 remittance limit
    s["f70"] = ["SETTLEMENT OF PROFORMA INVOICES NO", "8841 AND 8842 DATED 15 SEPTEMBER 26",
                "FOR SUPPLY OF GOODS UNDER CONTRACT", "77 AS PER AGREED DELIVERY SCHEDULE"]
    s["f70"] = [l[:35] for l in s["f70"]]
    return "DL_RMT_TRUNC_SUSPECT"
def _d10(s, rng):   # JPY has no minor units, but the amount carries decimals
    s["ccy"], s["amount"] = "JPY", Decimal(rng.randint(100000, 900000)) + Decimal("0.50")
    s["f33b"] = s["f36"] = None
    s["feats"][:] = [f for f in s["feats"] if f != "FX_33B_36"]
    s["f71f"] = [f"JPY{rng.randint(500, 2000)},"] if s["f71f"] else []
    s["f71g"] = [f"JPY{rng.randint(500, 2000)},"] if s["f71g"] else []
    return "BR_AMT_DECIMALS"


def _d11(s, rng): s["ccy"] = "XYZ"; s["f33b"] = s["f36"] = None; s["f71f"] = s["f71g"] = []; s["f71a"] = "SHA"; return "BR_CCY_UNKNOWN"
def _d12(s, rng): s["raw_date"] = rng.choice(["260231", "261331", "260931"]) ; return "SX_DATE_INVALID"
def _d13(s, rng): s["amount_text"] = str(int(s["amount"])); return "SX_AMOUNT_FORMAT"
def _d15(s, rng): s["f71a"] = "OUR"; s["f71g"] = []; s["f71f"] = [f"{s['ccy']}15,00"]; return "BR_CHRG_RULE"
def _d16(s, rng):
    other = "EUR" if s["ccy"] != "EUR" else "USD"; s["f33b"] = (other, (s["amount"] * Decimal("0.92")).quantize(Decimal("0.01"))); s["f36"] = None; return "BR_FX_RATE_MISSING"
def _d17(s, rng): s["date"] = s["date"] + dt.timedelta(days=(5 - s["date"].weekday()) + rng.choice([0, 1])); return "BR_VALUE_DATE_WEEKEND"
def _d18(s, rng):
    p = s["cdtr"] if len(s["cdtr"]["acct"]) > 12 else s["dbtr"]
    other = "AE" if p["cc"] != "AE" else "GB"
    p["addr"], p["town"] = _addr(rng, other); return "BR_IBAN_ADDR_MISMATCH"
def _d19(s, rng): s["drop"] = [rng.choice(["59", "71A", "20"])]; return "SX_MISSING_FIELD"
def _d22(s, rng): s["cdtr"]["acct"] = "".join(str(rng.randint(0, 9)) for _ in range(12)); return "BR_NON_IBAN_ACCT"

DEFECTS = [  # (label, count, function, applicability predicate)
    ("D01_IBAN_CHECKSUM", 4, _d01, lambda s: _iban_party(s) is not None),
    ("D02_IBAN_LENGTH", 2, _d02, lambda s: _iban_party(s) is not None),
    ("D03_BIC_FORMAT", 4, _d03, lambda s: True),
    ("D06_ADDR_NO_COUNTRY", 5, _d06, lambda s: True),
    ("D07_ADDR_TOWN_ONLY", 3, _d07, lambda s: s["cdtr"]["cc"] in ("PK", "AE", "SA") or s["dbtr"]["cc"] in ("PK", "AE", "SA")),
    ("D08_NAME_AT_35", 3, _d08, lambda s: s["cdtr"]["opt"] == "K" or s["dbtr"]["opt"] == "K"),
    ("D09_REMIT_FULL", 3, _d09, lambda s: True),
    ("D10_JPY_DECIMALS", 2, _d10, lambda s: True),
    ("D11_UNKNOWN_CCY", 2, _d11, lambda s: True),
    ("D12_BAD_DATE", 2, _d12, lambda s: True),
    ("D13_AMOUNT_NO_COMMA", 2, _d13, lambda s: True),
    ("D15_CHARGE_RULE", 2, _d15, lambda s: True),
    ("D16_FX_NO_RATE", 2, _d16, lambda s: True),
    ("D17_WEEKEND_DATE", 2, _d17, lambda s: True),
    ("D18_IBAN_COUNTRY_MISMATCH", 2, _d18, lambda s: len(s["cdtr"]["acct"]) > 12 or len(s["dbtr"]["acct"]) > 12),
    ("D19_MISSING_MANDATORY", 2, _d19, lambda s: True),
    ("D22_NON_IBAN_PK_ACCOUNT", 4, _d22, lambda s: s["cdtr"]["cc"] == "PK"),
]


def generate(out_dir: str, n: int = 100):
    rng = random.Random(SEED)
    scen = ["S1"] * 40 + ["S2"] * 25 + ["S3"] * 25 + ["S4"] * 10
    rng.shuffle(scen)
    specs = [build_spec(rng, i + 1, scen[i]) for i in range(n)]
    free = list(range(n))
    rng.shuffle(free)
    for label, count, fn, ok in DEFECTS:
        placed = 0
        for idx in list(free):
            s = specs[idx]
            if ok(s) and not s["defects"]:
                expected = fn(s, rng)
                s["defects"].append((label, expected))
                free.remove(idx); placed += 1
                if placed == count: break
        assert placed == count, (label, placed)
    os.makedirs(os.path.join(out_dir, "mt103"), exist_ok=True)
    rows = []
    for s in specs:
        text = render(s)
        with open(os.path.join(out_dir, "mt103", s["id"] + ".txt"), "w") as f:
            f.write(text + "\n")
        rows.append([s["id"], s["scenario"], s["corridor"], s["ccy"], f"{s['amount']:.2f}",
                     ";".join(d[0] for d in s["defects"]), ";".join(d[1] for d in s["defects"]), ";".join(s["feats"])])
    with open(os.path.join(out_dir, "manifest.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["msg_id", "scenario", "corridor", "currency", "amount", "injected_defect", "expected_rule", "features"])
        w.writerows(rows)
    return rows
