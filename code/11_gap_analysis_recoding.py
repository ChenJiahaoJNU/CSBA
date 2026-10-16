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
"""What the full approval-date sweep implies for the cohort design.

Ordering convention (the CORRECTED one, see _paperA_timing_fix.py): higher =
later. 1..4 = 2025Q1..Q4, 5 = 2026, 6 = never abolished. The dta ships
cohort_ord with 0 = never, which is the inverted convention, so it is re-coded
here before anything is estimated.

Question: the paper codes cohorts on the FIRST ANNOUNCEMENT date (the board
proposal). The shareholder vote comes later. For how many firms does that move
them across a quarterly boundary, and does coding on the approval date instead
change the ordered-logit conclusion?
"""
import numpy as np
import pandas as pd
from statsmodels.miscmodels.ordinal_model import OrderedModel

DC = os.path.join(OUT, "datecheck", "gap_full.csv")
DTA = os.path.join(OUT, "paperA_estimation.dta")

# ------------------------------------------------------------------ the sweep
g = pd.read_csv(DC, dtype={"code": str})
g["code"] = g["code"].str.zfill(6)
g["ann"] = pd.to_datetime(g["ann"], errors="coerce")
g["meet"] = pd.to_datetime(g["meet"], errors="coerce")
ok = g[g["meet"].notna()].copy()
ok["gap"] = (ok["meet"] - ok["ann"]).dt.days

print("=" * 78)
print("A. APPROVAL-DATE SWEEP (all firms, not a 30-firm sample)")
print("=" * 78)
print("firms swept              : %d" % len(g))
print("approval resolved        : %d (%.1f%%)" % (len(ok), 100 * len(ok) / len(g)))
print("impossible (gap < 0)     : %d   <- extraction noise" % (ok.gap < 0).sum())
print()
print("gap (days) quantiles:")
print(ok.gap.quantile([.05, .10, .25, .50, .75, .90, .95]).round(0).to_string())
print()
sq = (ok.meet.dt.to_period("Q") == ok.ann.dt.to_period("Q")).mean()
sm = (ok.meet.dt.to_period("M") == ok.ann.dt.to_period("M")).mean()
print("approval in SAME quarter as proposal : %.1f%%  <-- cohort cell is right" % (100 * sq))
print("approval in SAME month  as proposal  : %.1f%%" % (100 * sm))
print("approval in SAME year   as proposal  : %.1f%%"
      % (100 * (ok.meet.dt.year == ok.ann.dt.year).mean()))

# ------------------------------------------------------------------ re-code
p = pd.read_stata(DTA).rename(columns={
    "roa_y22_w": "roa", "leverage_y22_w": "lev", "institution_y22_w": "inst",
    "asy_y22_w": "asy", "riskdisclosure_y22_w": "riskdisc", "esg_y22_w": "esg",
    "textsimilarity_y22_w": "textsim", "analyst_log": "anlog"})
p["logassets_z"] = (p.logassets - p.logassets.mean()) / p.logassets.std()
p["code"] = p["stkcd"].astype(str).str.zfill(6)

QM = {"2025Q1": 1, "2025Q2": 2, "2025Q3": 3, "2025Q4": 4,
      "2026Q1": 5, "2026Q2": 5, "2026Q3": 5, "2026Q4": 5}


def to_periods(s):
    return s.dt.to_period("Q").astype(str).map(QM)


# announcement-based, corrected ordering
p["c_ann"] = p["cohort_quarter"].map(QM)
p.loc[p.abolish_ever == 0, "c_ann"] = 6
# approval-based, same ordering
m = p.merge(ok[["code", "meet", "gap"]], on="code", how="left")
m["c_app"] = to_periods(m["meet"])
m.loc[m.abolish_ever == 0, "c_app"] = 6
unres = (m.abolish_ever == 1) & m.c_app.isna()
print()
print("treated with unresolved approval date (fall back to announcement): %d"
      % unres.sum())
m.loc[unres, "c_app"] = m.loc[unres, "c_ann"]

TERMS = ["roa", "lev", "logassets_z", "inst", "asy", "riskdisc", "esg", "textsim"]
BASE = m.dropna(subset=TERMS + ["abolish_ever", "industrycode", "c_ann",
                                "c_app"]).copy()
print("BASE N=%d  treated=%d" % (len(BASE), BASE.abolish_ever.sum()))

print()
print("=" * 78)
print("B. COHORT CELLS: proposal date vs approval date (1=Q1..4=Q4, 5=2026, 6=never)")
print("=" * 78)
ct = pd.crosstab(BASE["c_ann"], BASE["c_app"])
print(ct.to_string())
tr = BASE[BASE.abolish_ever == 1]
moved = (tr.c_ann != tr.c_app).sum()
print()
print("treated firms that CHANGE cohort cell: %d of %d (%.1f%%)"
      % (moved, len(tr), 100 * moved / len(tr)))

print()
print("=" * 78)
print("C. ORDERED LOGIT -- does the conclusion depend on which date defines the cohort?")
print("=" * 78)
for lab, col in (("proposal/announcement date (as in the paper)", "c_ann"),
                 ("shareholder-approval date", "c_app")):
    y = BASE[col].astype(int)
    om = OrderedModel(y, BASE[TERMS], distr="logit").fit(method="bfgs", disp=0)
    print()
    print("--- %s ---" % lab)
    print("  cells: %s" % dict(y.value_counts().sort_index()))
    print("  N=%d   LR p=%.4g   pseudo-R2=%.4f" % (len(y), om.llr_pvalue, om.prsquared))
    for t in ["asy", "inst", "roa", "logassets_z", "riskdisc", "textsim"]:
        b, se, pv = om.params[t], om.bse[t], om.pvalues[t]
        st = "***" if pv < .01 else "**" if pv < .05 else "*" if pv < .1 else ""
        print("    %-13s %+7.3f (se %.3f, p=%.3f)%s" % (t, b, se, pv, st))
