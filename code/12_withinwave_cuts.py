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
"""Do the two within-wave cuts stay insignificant under approval-date cohorts?

Paper A reports both cuts on announcement-date cohorts: 2025H1 vs 2025H2 gives
asy +0.155 (p=0.50); 2025Q4 vs all earlier gives asy -0.50 (p<0.01). Since 58.9%
of treated firms change cohort cell when coded on the shareholder-approval date,
the same two cuts are re-run here on approval cohorts.
"""
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

p = pd.read_stata(os.path.join(OUT, "paperA_estimation.dta")).rename(columns={
    "roa_y22_w": "roa", "leverage_y22_w": "lev", "institution_y22_w": "inst",
    "asy_y22_w": "asy", "riskdisclosure_y22_w": "riskdisc", "esg_y22_w": "esg",
    "textsimilarity_y22_w": "textsim", "analyst_log": "anlog"})
p["logassets_z"] = (p.logassets - p.logassets.mean()) / p.logassets.std()
p["code"] = p["stkcd"].astype(str).str.zfill(6)

g = pd.read_csv(os.path.join(OUT, "datecheck", "gap_full.csv"), dtype={"code": str})
g["code"] = g["code"].str.zfill(6)
g["meet"] = pd.to_datetime(g["meet"], errors="coerce")
m = p.merge(g[["code", "meet"]], on="code", how="left")

QS = {"2025Q1": 1, "2025Q2": 2, "2025Q3": 3, "2025Q4": 4,
      "2026Q1": 5, "2026Q2": 5, "2026Q3": 5, "2026Q4": 5}
m["q_app"] = m["meet"].dt.to_period("Q").astype(str).map(QS)
m["q_ann"] = m["cohort_quarter"].map(QS)

TERMS = ["roa", "lev", "logassets_z", "inst", "asy", "riskdisc", "esg", "textsim"]
CORE, INFO = "roa + lev + logassets_z", "inst + asy + riskdisc + esg + textsim"
F = "{dv} ~ " + CORE + " + " + INFO + " + C(industrycode)"


def run(dv, data, label):
    d = data.dropna(subset=[dv] + TERMS).copy()
    g_ = d.groupby("industrycode")[dv].agg(["size", "mean"])
    keep = g_[(g_["size"] >= 10) & (g_["mean"] > 0) & (g_["mean"] < 1)].index
    d = d[d.industrycode.isin(keep)]
    mm = smf.logit(F.format(dv=dv), data=d).fit(disp=0, cov_type="HC1")
    star = lambda pv: "***" if pv < .01 else "**" if pv < .05 else "*" if pv < .1 else ""
    print("  %-46s N=%-5d ev=%-4d asy %+6.3f (p=%.3f)%s"
          % (label, len(d), int(d[dv].sum()), mm.params["asy"],
             mm.pvalues["asy"], star(mm.pvalues["asy"])))
    return mm


tr = m[m.abolish_ever == 1].copy()
print("=== within-wave cuts, ANNOUNCEMENT cohorts (as the paper reports) ===")
tr["h1_ann"] = (tr.q_ann <= 2).astype(float)
tr["q4_ann"] = (tr.q_ann == 4).astype(float)
run("h1_ann", tr, "2025H1 (1) vs 2025H2 (0)")
run("q4_ann", tr, "2025Q4 (1) vs all earlier (0)")

print()
print("=== within-wave cuts, APPROVAL cohorts ===")
t2 = tr[tr.q_app.notna()].copy()
print("  (treated with a resolved approval quarter: %d of %d)" % (len(t2), len(tr)))
t2["h1_app"] = (t2.q_app <= 2).astype(float)
t2["q4_app"] = (t2.q_app == 4).astype(float)
run("h1_app", t2, "2025H1 (1) vs 2025H2 (0)")
run("q4_app", t2, "2025Q4 (1) vs all earlier (0)")

print()
print("=== same two cuts on the same subsample, announcement cohorts (fair compare) ===")
t2["h1_ann"] = (t2.q_ann <= 2).astype(float)
t2["q4_ann"] = (t2.q_ann == 4).astype(float)
run("h1_ann", t2, "2025H1 (1) vs 2025H2 (0)")
run("q4_ann", t2, "2025Q4 (1) vs all earlier (0)")
