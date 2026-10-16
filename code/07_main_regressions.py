# -*- coding: utf-8 -*-
"""Replication script for:

    Who gives up the independent monitor? Board reform and the abolition of
    China's supervisory board.

Paths come from config.py so the package is relocatable. Set the environment
variables PAPER_A_VENDOR (licensed inputs you must obtain yourself) and
PAPER_A_OUT (where outputs are written) before running.
"""
from config import ROOT, DATA, VENDOR, OUT, MANUSCRIPT  # noqa: F401

# -*- coding: utf-8 -*-
"""Paper A regressions, v3 -- the definitive run.

Fixes vs v2:
  * v2 used `dropna(subset=[...] or None)`; with an empty list that evaluates to
    None and pandas then drops rows with ANY missing value across all 49 columns,
    so specs (1)-(2) silently ran on N=1,941 while spec (3) ran on N=3,689.
    All specifications now run on the SAME sample.
  * province FE was singular because some provinces are perfectly predicted;
    degenerate provinces (single treatment status, or <20 firms) are dropped.
"""
import os
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.miscmodels.ordinal_model import OrderedModel
p = pd.read_stata(os.path.join(OUT, "paperA_estimation.dta")).rename(columns={
    "roa_y22_w": "roa", "leverage_y22_w": "lev", "institution_y22_w": "inst",
    "asy_y22_w": "asy", "riskdisclosure_y22_w": "riskdisc", "esg_y22_w": "esg",
    "textsimilarity_y22_w": "textsim", "analyst_log": "anlog"})
p["logassets_z"] = (p.logassets - p.logassets.mean()) / p.logassets.std()
p["cohort"] = p["cohort_ord"].clip(upper=4)

TERMS = ["roa", "lev", "logassets_z", "inst", "asy", "riskdisc", "esg", "textsim"]
BASE = p.dropna(subset=TERMS + ["abolish_ever", "cohort", "industrycode"]).copy()

# degenerate industry / province groups (perfect prediction -> singular matrix)
def prune(df, col, minn=20):
    g = df.groupby(col)["abolish_ever"].agg(["size", "mean"])
    keep = g[(g["size"] >= minn) & (g["mean"] > 0) & (g["mean"] < 1)].index
    return df[df[col].isin(keep)].copy()

b_ind = prune(BASE, "industrycode")
b_prov = prune(BASE, "provincecode")
print("BASE      N=%d treated=%d (%.1f%%)" %
      (len(BASE), BASE.abolish_ever.sum(), 100 * BASE.abolish_ever.mean()))
print("ind-pruned N=%d over %d industries" % (len(b_ind), b_ind.industrycode.nunique()))
print("prov-pruned N=%d over %d provinces" % (len(b_prov), b_prov.provincecode.nunique()))

CORE = "roa + lev + logassets_z"
INFO = "inst + asy + riskdisc + esg + textsim"

def fit(formula, data, se="hc1", cluster=None):
    if se == "cluster":
        return smf.logit(formula, data=data).fit(
            disp=0, cov_type="cluster",
            cov_kwds={"groups": data[cluster].astype("category").cat.codes})
    return smf.logit(formula, data=data).fit(disp=0, cov_type="HC1")

SPECS = [
    ("(1) firm chars",    f"abolish_ever ~ {CORE}", BASE, "hc1", None),
    ("(2) + gov/info",    f"abolish_ever ~ {CORE} + {INFO}", BASE, "hc1", None),
    ("(3) + industry FE", f"abolish_ever ~ {CORE} + {INFO} + C(industrycode)",
     b_ind, "hc1", None),
    ("(4) + province FE", f"abolish_ever ~ {CORE} + {INFO} + C(provincecode)",
     b_prov, "hc1", None),
    ("(5) ind clust SE",  f"abolish_ever ~ {CORE} + {INFO}",
     b_ind, "cluster", "industrycode"),
]
fits = {}
print()
print("=" * 104)
print("LOGIT   LHS = abolish_ever (abolished by 2025-12-31)")
print("=" * 104)
for name, f, d, se, cl in SPECS:
    try:
        m = fit(f, d, se, cl)
        fits[name] = (m, len(d), int(d.abolish_ever.sum()))
    except Exception as e:
        print("%-18s FAILED %s" % (name, str(e)[:70]))

print("%-13s" % "variable" + "".join("%18s" % n for n, *_ in SPECS if n in fits))
print("-" * 104)
for t in TERMS:
    row = "%-13s" % t
    for name, *_ in SPECS:
        if name not in fits:
            continue
        m = fits[name][0]
        if t in m.params.index:
            b, s, pv = m.params[t], m.bse[t], m.pvalues[t]
            st = "***" if pv < .01 else "**" if pv < .05 else "*" if pv < .1 else ""
            row += "%18s" % ("%+.3f%s(%.3f)" % (b, st, s))
        else:
            row += "%18s" % "."
    print(row)
print("-" * 104)
for n, (m, nn, ev) in fits.items():
    print("  %-18s N=%-5d events=%-5d pseudo-R2=%.4f" % (n, nn, ev, m.prsquared))

print()
print("=== average marginal effects, spec (3), percentage points ===")
m3 = fits["(3) + industry FE"][0]
me = m3.get_margeff(at="overall")
sf = me.summary_frame()
for t in TERMS:
    if t in sf.index:
        b, s, pv = me.margeff[sf.index.get_loc(t)], me.margeff_se[sf.index.get_loc(t)], me.pvalues[sf.index.get_loc(t)]
        st = "***" if pv < .01 else "**" if pv < .05 else "*" if pv < .1 else ""
        print("  %-13s %+8.2f pp (se %5.2f) p=%.3f %s" % (t, 100*b, 100*s, pv, st))
print("  NOTE: textsim and riskdisc have tiny scales; see per-SD table below.")

print()
print("=== per standard deviation (spec 3 coefficients x sd) ===")
for t in TERMS:
    if t in m3.params.index:
        sd = BASE[t].std()
        print("  %-13s sd=%.4f -> logit coef %.3f  (=%.3f per sd)" %
              (t, sd, m3.params[t], m3.params[t] * sd))

print()
print("=" * 104)
print("ORDERED LOGIT   LHS = cohort (0 never .. 4 = 2025Q4)")
print("=" * 104)
om = OrderedModel(BASE["cohort"], BASE[TERMS], distr="logit").fit(method="bfgs", disp=0)
print("N=%d" % len(BASE))
for t in TERMS:
    b, s, pv = om.params[t], om.bse[t], om.pvalues[t]
    st = "***" if pv < .01 else "**" if pv < .05 else "*" if pv < .1 else ""
    print("  %-13s %+8.4f (%.4f) p=%.4f %s" % (t, b, s, pv, st))

# ---- save the headline spec's full output ----
with open(os.path.join(OUT, "regression_output.txt"), "w", encoding="utf-8") as f:
    for name, (m, nn, ev) in fits.items():
        f.write("\n===== %s  (N=%d, events=%d) =====\n" % (name, nn, ev))
        f.write(str(m.summary()) + "\n")
    f.write("\n===== ORDERED LOGIT =====\n")
    f.write(str(om.summary()) + "\n")
print("\nsaved: paperA/regression_output.txt")
