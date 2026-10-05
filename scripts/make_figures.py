import json, os, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
S = json.load(open("output/summary.json"))
NAVY, TEAL, AMB, RED, GREY = "#1F3A5F", "#2A9D8F", "#E9C46A", "#E76F51", "#8D99AE"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})

# 1 status
fig, ax = plt.subplots(figsize=(6.2, 3.2))
order = ["PASS_CLEAN", "PASS_WITH_WARNINGS", "FAILED_VALIDATION", "REJECTED"]
vals = [S["status"].get(k, 0) for k in order]
b = ax.bar(["Clean", "With warnings", "Failed\nvalidation", "Rejected\nat parse"], vals, color=[TEAL, AMB, RED, "#9B2226"])
for r, v in zip(b, vals): ax.text(r.get_x() + r.get_width() / 2, v + 0.8, str(v), ha="center", fontweight="bold")
ax.set_ylabel("Messages"); ax.set_ylim(0, max(vals) * 1.2); ax.spines[["top", "right"]].set_visible(False)
ax.set_title("Migration outcome of 100 synthetic MT103 messages", fontsize=11)
fig.tight_layout(); fig.savefig("docs/fig/status.png", dpi=200); plt.close()

# 2 provenance by group
g = S["lineage_by_group"]
groups = sorted(g, key=lambda k: -sum(g[k].values()))[:12]
meths = [("DIRECT", NAVY), ("CODE", "#3D5A80"), ("PARSED", AMB), ("INFERRED", RED), ("FREETEXT", GREY)]
fig, ax = plt.subplots(figsize=(6.4, 3.8))
left = [0] * len(groups)
for m, c in meths:
    v = [g[k].get(m, 0) / sum(g[k].values()) * 100 for k in groups]
    ax.barh(groups, v, left=left, color=c, label=m)
    left = [a + b for a, b in zip(left, v)]
ax.invert_yaxis(); ax.set_xlabel("% of populated leaf elements"); ax.legend(ncol=5, fontsize=7, loc="lower center", bbox_to_anchor=(0.5, 1.0), frameon=False)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig("docs/fig/lineage.png", dpi=200); plt.close()

# 3 address by country
a = S["address_by_country"]
cs = sorted(a)
fig, ax = plt.subplots(figsize=(6.2, 3.2))
import numpy as np
x = np.arange(len(cs)); w = 0.38
ax.bar(x - w / 2, [a[c]["town_country"] / a[c]["parties"] * 100 for c in cs], w, color=TEAL, label="Town + country found")
ax.bar(x + w / 2, [a[c]["street"] / a[c]["parties"] * 100 for c in cs], w, color=AMB, label="Street / building structured")
ax.set_xticks(x); ax.set_xticklabels([f"{c}\n(n={a[c]['parties']})" for c in cs], fontsize=8)
ax.set_ylabel("% of parties"); ax.set_ylim(0, 125); ax.legend(fontsize=8, frameon=False, loc="upper center", ncol=2)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig("docs/fig/address.png", dpi=200); plt.close()

# 4 recall
r = S["recall_by_defect"]
fig, ax = plt.subplots(figsize=(6.4, 4.4))
names = list(r)
ax.barh(names, [r[n]["detected"] / r[n]["injected"] * 100 for n in names], color=TEAL)
for i, n in enumerate(names): ax.text(101, i, f"{r[n]['detected']}/{r[n]['injected']}", va="center", fontsize=8)
ax.set_xlim(0, 115); ax.invert_yaxis(); ax.set_xlabel("Recall (%)"); ax.tick_params(axis="y", labelsize=7.5)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig("docs/fig/recall.png", dpi=200); plt.close()

# 5 architecture
fig, ax = plt.subplots(figsize=(7, 2.9)); ax.axis("off"); ax.set_xlim(0, 100); ax.set_ylim(0, 40)
boxes = [(1, "MT103\nparser", NAVY), (19, "Mapper\n(+ lineage)", NAVY), (37, "pacs.008\nXML", TEAL), (55, "Validator\nXSD + rules", NAVY), (73, "Analyzer\n+ scoring", NAVY)]
for x, t, c in boxes:
    ax.add_patch(FancyBboxPatch((x, 16), 16, 14, boxstyle="round,pad=0.4", fc=c, ec="none"))
    ax.text(x + 8, 23, t, ha="center", va="center", color="white", fontsize=9, fontweight="bold")
for x in (17.4, 35.4, 53.4, 71.4): ax.annotate("", xy=(x + 1.8, 23), xytext=(x - 0.2, 23), arrowprops=dict(arrowstyle="->", color="#333"))
ax.text(9, 10, "SWIFT FIN text", ha="center", fontsize=8, color="#444"); ax.text(27, 10, "address heuristics,\ncode-word tables", ha="center", fontsize=8, color="#444")
ax.text(63, 10, "20+ business rules,\nCBPR+ address check", ha="center", fontsize=8, color="#444"); ax.text(81, 10, "loss / guess / gain\nfindings, score", ha="center", fontsize=8, color="#444")
ax.add_patch(FancyBboxPatch((55, 31), 34, 6, boxstyle="round,pad=0.3", fc="#DCE6F1", ec="none"))
ax.text(72, 34, "Results CSV  ->  Excel dashboard + business case", ha="center", va="center", fontsize=8.5)
ax.add_patch(FancyBboxPatch((1, 31), 34, 6, boxstyle="round,pad=0.3", fc="#DCE6F1", ec="none"))
ax.text(18, 34, "Synthetic dataset + ground-truth manifest", ha="center", va="center", fontsize=8.5)
fig.tight_layout(); fig.savefig("docs/fig/arch.png", dpi=200); plt.close()
print("figs ok")
