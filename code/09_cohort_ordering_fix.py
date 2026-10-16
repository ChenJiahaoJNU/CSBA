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
"""FIX the ordered-logit cohort coding and re-interpret the timing result.

The bug: cohort_ord was coded 0 = never abolished, 1..4 = 2025 Q1..Q4. In an
ordered logit the categories must be ORDERED by the underlying construct. "Never
abolished" is the LATEST state, not the earliest, so putting it at 0 made the
model treat never-adopters as the most eager. Signs were therefore read backwards.

Correct coding: 1 = 2025Q1 ... 4 = 2025Q4, 5 = 2026, 6 = never.
"""
import os
import numpy as np
import pandas as pd
from statsmodels.miscmodels.ordinal_model import OrderedModel
import statsmodels.formula.api as smf
p = pd.read_stata(os.path.join(OUT, "paperA_estimation.dta")).rename(columns={
    "roa_y22_w": "roa", "leverage_y22_w": "lev", "institution_y22_w": "inst",
    "asy_y22_w": "asy", "riskdisclosure_y22_w": "riskdisc", "esg_y22_w": "esg",
    "textsimilarity_y22_w": "textsim", "analyst_log": "anlog"})
p["logassets_z"] = (p.logassets - p.logassets.mean()) / p.logassets.std()

TERMS = ["roa", "lev", "logassets_z", "inst", "asy", "riskdisc", "esg", "textsim"]
BASE = p.dropna(subset=TERMS + ["abolish_ever", "industrycode"]).copy()

# ---- corrected ordering: never = LATEST ----
QMAP = {"2025Q1": 1, "2025Q2": 2, "2025Q3": 3, "2025Q4": 4,
        "2026Q1": 5, "2026Q2": 5}
BASE["cohort_fixed"] = BASE["cohort_quarter"].map(QMAP)
BASE["cohort_fixed"] = BASE["cohort_fixed"].fillna(6).astype(int)   # never = 6
print("cohort_fixed distribution (1=Q1 .. 4=Q4, 5=2026, 6=never):")
print(BASE.cohort_fixed.value_counts().sort_index().to_string())

print()
print("=" * 100)
print("ORDERED LOGIT -- CORRECTED ordering (higher = later / never)")
print("=" * 100)
om = OrderedModel(BASE["cohort_fixed"], BASE[TERMS], distr="logit").fit(
    method="bfgs", disp=0)
print("N=%d" % len(BASE))
print("%-13s %10s %9s %8s   %s" % ("variable", "coef", "se", "p", "reading"))
for t in TERMS:
    b, s, pv = om.params[t], om.bse[t], om.pvalues[t]
    st = "***" if pv < .01 else "**" if pv < .05 else "*" if pv < .1 else ""
    direction = "LATER/never" if b > 0 else "EARLIER"
    print("%-13s %10.4f %9.4f %8.4f %s  higher value -> %s" %
          (t, b, s, pv, st, direction if pv < .1 else "(n.s.)"))

print()
print(">>> INTERPRETATION: a NEGATIVE coefficient means a higher covariate value")
print("    is associated with an EARLIER cohort, i.e. earlier abolition.")
print("    A POSITIVE coefficient means later abolition or never.")

# ---- cross-check with two clean binary splits ----
print()
print("=" * 100)
print("CROSS-CHECK: two unambiguous binary comparisons")
print("=" * 100)
CORE, INFO = "roa + lev + logassets_z", "inst + asy + riskdisc + esg + textsim"
F = f"{{dv}} ~ {CORE} + {INFO} + C(industrycode)"


def fit(dv, data, label):
    d = data.dropna(subset=[dv]).copy()
    g = d.groupby("industrycode")[dv].agg(["size", "mean"])
    keep = g[(g["size"] >= 10) & (g["mean"] > 0) & (g["mean"] < 1)].index
    d = d[d.industrycode.isin(keep)]
    m = smf.logit(F.format(dv=dv), data=d).fit(disp=0, cov_type="HC1")
    print("\n%s   N=%d  events=%d" % (label, len(d), int(d[dv].sum())))
    for t in ["roa", "logassets_z", "inst", "asy", "riskdisc", "esg", "textsim"]:
        if t in m.params.index:
            b, pv = m.params[t], m.pvalues[t]
            st = "***" if pv < .01 else "**" if pv < .05 else "*" if pv < .1 else ""
            print("   %-13s %+.3f%s (p=%.3f)" % (t, b, st, pv))
    return m


fit("abolish_ever", BASE, "A) ever abolished (1) vs never (0)")
within = BASE[BASE.abolish_ever == 1].copy()
within["early"] = (within.cohort_fixed <= 2).astype(int)   # Q1-Q2 vs Q3-Q4
fit("early", within, "B) WITHIN the wave: early (2025H1) vs late (2025H2)")
