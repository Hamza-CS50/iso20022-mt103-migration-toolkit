import json, sys, os, csv
sys.path.insert(0, ".")
from mt2iso.validator import RULES
from openpyxl import load_workbook
S = json.load(open("output/summary.json"))

def scenario(idx):
    inp = {"Conservative": dict(v=400000, rr=.025, cut=.15, cr=8, ar=.02, fp=.05, ca=6, one=900000, run=150000, d=.12, g=.02, us=.40, nak=.02, cn=20),
           "Base": dict(v=600000, rr=.04, cut=.30, cr=12, ar=.03, fp=.12, ca=10, one=650000, run=110000, d=.10, g=.05, us=.58, nak=.05, cn=30),
           "Optimistic": dict(v=800000, rr=.055, cut=.45, cr=16, ar=.04, fp=.20, ca=14, one=500000, run=80000, d=.08, g=.08, us=.60, nak=.10, cn=45)}[idx]
    i = inp; npv_all = -i["one"]; npv_ops = -i["one"]; cum = -i["one"]; payback = None; flows = [-i["one"]]
    for y in range(1, 6):
        vol = i["v"] * (1 + i["g"]) ** (y - 1)
        ops = vol * i["rr"] * i["cut"] * i["cr"] + vol * i["ar"] * i["fp"] * i["ca"]
        nak = vol * i["us"] * i["nak"] * i["cn"]
        df = 1 / (1 + i["d"]) ** y
        npv_all += (ops + nak - i["run"]) * df; npv_ops += (ops - i["run"]) * df
        cum += ops + nak - i["run"]; flows.append(ops + nak - i["run"])
        if payback is None and cum >= 0: payback = y
    lo, hi = -0.99, 50.0
    f = lambda r: sum(c / (1 + r) ** t for t, c in enumerate(flows))
    for _ in range(200):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if f(mid) > 0 else (lo, mid)
    return dict(npv_all=npv_all, npv_ops=npv_ops, payback=payback, irr=(lo + hi) / 2, inputs=inp)

sc = {k: scenario(k) for k in ("Conservative", "Base", "Optimistic")}
wb = load_workbook("output/ISO20022_Migration_Dashboard.xlsx", data_only=True)
b = wb["Business Case"]
assert abs(b["B37"].value - sc["Base"]["npv_all"]) < 1, (b["B37"].value, sc["Base"]["npv_all"])   # cross-check Python vs workbook
assert abs(b["B38"].value - sc["Base"]["npv_ops"]) < 1

# worked example
mt = open("data/mt103/MSG002.txt").read()
xml = open("output/pacs008/MSG002.xml").read()
find = [r for r in csv.DictReader(open("output/findings.csv")) if r["msg_id"] == "MSG002"]
D = dict(summary=S, scenarios=sc, rules=[[k, *v] for k, v in RULES.items()], example_mt=mt, example_xml=xml, example_findings=find,
         scen_counts={"S1": 40, "S2": 25, "S3": 25, "S4": 10})
json.dump(D, open("docs/report_data.json", "w"), indent=1)
print({k: (round(v["npv_all"]), round(v["npv_ops"]), v["payback"], round(v["irr"], 2)) for k, v in sc.items()})
print(find)
