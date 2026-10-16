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
"""Paper A robustness battery.

Tests
 R1 drop the 2025Q4 sprint cohort (DV = abolished by 2025Q3)
 R2 industry x province fixed effects
 R3 alternative information-asymmetry proxies
      ncskew (crash risk / tail asymmetry), analyst coverage (intermediation),
      |roa - cashflow| (accrual-magnitude proxy)
 R4 covariates dated FY2023 instead of FY2022 (still pre-2024 reform)
 R5 probit instead of logit (functional form)
 R6 placebo: predict a pre-period outcome that should be unrelated to the reform
 R7 entropy-style balance: is the treated/control split balanced on observables?
"""
import os
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
p = pd.read_stata(os.path.join(OUT, "paperA_estimation.dta")).rename(columns={
    "roa_y22_w": "roa", "leverage_y22_w": "lev", "institution_y22_w": "inst",
    "asy_y22_w": "asy", "riskdisclosure_y22_w": "riskdisc", "esg_y22_w": "esg",
    "textsimilarity_y22_w": "textsim", "analyst_log": "anlog",
    "ncskew_y22_w": "ncskew"})
p["logassets_z"] = (p.logassets - p.logassets.mean()) / p.logassets.std()
p["cohort"] = p["cohort_ord"].clip(upper=4)
# cashflow was never merged into the Paper A estimation file (omitted from BLOCKS
# in _paperA_build.py), so pull it from the raw block here.
_cf = pd.read_stata(os.path.join(VENDOR_DATA, "2000-2023_Operating_Cashflow_to_Total_Assets.dta"))
_cf.columns = [c.strip().lower() for c in _cf.columns]
_cf["stkcd"] = pd.to_numeric(_cf["stkcd"], errors="coerce").astype("Int64")
_cf["year"] = pd.to_numeric(_cf["year"], errors="coerce").astype("Int64")
_cf = _cf[_cf.year == 2022][["stkcd", "cashflow"]]
p = p.merge(_cf, on="stkcd", how="left")
p["cashflow_w"] = p["cashflow"].clip(p["cashflow"].quantile(0.01),
                                     p["cashflow"].quantile(0.99))
p["accr"] = (p["roa"] - p["cashflow_w"]).abs()
print("cashflow merged: non-missing %d" % p["cashflow"].notna().sum())

TERMS = ["roa", "lev", "logassets_z", "inst", "asy", "riskdisc", "esg", "textsim"]
BASE = p.dropna(subset=TERMS + ["abolish_ever", "industrycode", "provincecode"]).copy()
print("BASE N=%d treated=%d" % (len(BASE), BASE.abolish_ever.sum()))

CORE, INFO = "roa + lev + logassets_z", "inst + asy + riskdisc + esg + textsim"
MAIN = f"{CORE} + {INFO} + C(industrycode)"


def prune(df, dv, col, minn=10):
    """Drop FE groups with a single treatment status or very few firms -- these
    make the design matrix singular in subsamples."""
    if col not in df.columns:
        return df
    g = df.groupby(col)[dv].agg(["size", "mean"])
    keep = g[(g["size"] >= minn) & (g["mean"] > 0) & (g["mean"] < 1)].index
    return df[df[col].isin(keep)].copy()


def run(label, dv, formula, data, extra=None):
    # `formula` is the RIGHT-HAND SIDE only; supply the LHS from `dv`.
    full = dv if "~" in formula else "%s ~ %s" % (dv, formula)
    d = data.dropna(subset=[dv])
    if "C(industrycode)" in full:
        d = prune(d, dv, "industrycode")
    if "C(provincecode)" in full:
        d = prune(d, dv, "provincecode")
    if "C(ip)" in full:
        g = d.groupby("ip")[dv].agg(["size", "mean"])
        keep = g[(g["size"] >= 10) & (g["mean"] > 0) & (g["mean"] < 1)].index
        d = d[d["ip"].isin(keep)]
    try:
        m = smf.logit(full, data=d).fit(disp=0, cov_type="HC1")
    except Exception as e:
        print("%-46s FAILED %s" % (label, str(e)[:60])); return None
    row = {"test": label, "N": len(d),
           "events": int(d[dv].sum()) if d[dv].dropna().isin([0, 1]).all() else -1,
           "pseudoR2": round(m.prsquared, 4)}
    for t in ["roa", "logassets_z", "inst", "asy", "riskdisc", "esg", "textsim"]:
        if t in m.params.index:
            b, pv = m.params[t], m.pvalues[t]
            st = "***" if pv < .01 else "**" if pv < .05 else "*" if pv < .1 else ""
            row[t] = "%+.2f%s" % (b, st)
        else:
            row[t] = ""
    if extra:
        for t in extra:
            if t in m.params.index:
                b, pv = m.params[t], m.pvalues[t]
                st = "***" if pv < .01 else "**" if pv < .05 else "*" if pv < .1 else ""
                row[t] = "%+.2f%s" % (b, st)
    return m, row


rows = []

# ---- baseline (v3 spec 3, recomputed for reference) ----
m0, r0 = run("baseline (industry FE)", "abolish_ever", MAIN, BASE)
rows.append(r0)

# ---- R1 drop the 2025Q4 sprint cohort ----
B1 = BASE.copy()
B1["early_only"] = np.where(B1["cohort_ord"].isin([1, 2, 3]), 1,
                   np.where(B1["cohort_ord"] == 0, 0, np.nan))
B1 = B1.dropna(subset=["early_only"])
m1, r1 = run("R1 abolition by 2025Q3 only (drop Q4)", "early_only", MAIN, B1)
rows.append(r1)

# ---- R1b: drop the never-abolished and keep only the wave, ordinal within  ----
B1b = BASE[BASE.cohort_ord > 0].copy()
B1b["late"] = (B1b.cohort_ord >= 4).astype(int)
m1b, r1b = run("R1b within-wave: Q4 vs earlier adopters", "late", MAIN, B1b)
rows.append(r1b)

# ---- R2 industry x province ----
B2 = BASE.copy()
g = B2.groupby(["industrycode", "provincecode"])["abolish_ever"].agg(["size", "mean"])
keep = g[(g["size"] >= 10) & (g["mean"] > 0) & (g["mean"] < 1)].index
B2["ip"] = list(zip(B2.industrycode, B2.provincecode))
B2 = B2[B2["ip"].isin(keep)]
m2, r2 = run("R2 industry x province FE", "abolish_ever",
             f"{CORE} + {INFO} + C(ip)", B2)
rows.append(r2)

# ---- R3 alternative asymmetry proxies ----
for nm, var in (("R3a ncskew (tail asymmetry)", "ncskew"),
                ("R3b analyst coverage", "anlog"),
                ("R3c |roa - cashflow| accrual proxy", "accr")):
    d = BASE.dropna(subset=[var])
    f = f"{CORE} + inst + {var} + riskdisc + esg + textsim + C(industrycode)"
    m, r = run(nm, "abolish_ever", f, d, extra=[var])
    if r: rows.append(r)

# ---- R4 FY2023 covariates ----
p23 = p.copy()
try:
    for c, c23 in (("roa", "roa_y23"), ("lev", "leverage_y23"),
                   ("inst", "institution_y23"), ("asy", "asy_y23"),
                   ("riskdisc", "riskdisclosure_y23"), ("esg", "esg_y23"),
                   ("textsim", "textsimilarity_y23")):
        if c23 in p23.columns:
            p23[c] = p23[c23]
    p23["logassets_z"] = (np.log(p23["assets_y23"].where(p23["assets_y23"] > 0))
                          - np.log(p23["assets_y23"].where(p23["assets_y23"] > 0)).mean()) \
                         / np.log(p23["assets_y23"].where(p23["assets_y23"] > 0)).std()
    B4 = p23.dropna(subset=TERMS + ["abolish_ever", "industrycode"])
    m4, r4 = run("R4 covariates dated FY2023", "abolish_ever", MAIN, B4)
    rows.append(r4)
    print("  (R4 used FY2023 replacements where available)")
except Exception as e:
    print("R4 skipped:", str(e)[:90])

# ---- R5 probit ----
try:
    m5 = smf.probit(MAIN, data=BASE).fit(disp=0, cov_type="HC1")
    r5 = {"test": "R5 probit (functional form)", "N": len(BASE),
          "events": int(BASE.abolish_ever.sum()), "pseudoR2": round(m5.prsquared, 4)}
    for t in ["roa", "logassets_z", "inst", "asy", "riskdisc", "esg", "textsim"]:
        if t in m5.params.index:
            b, pv = m5.params[t], m5.pvalues[t]
            st = "***" if pv < .01 else "**" if pv < .05 else "*" if pv < .1 else ""
            r5[t] = "%+.2f%s" % (b, st)
    rows.append(r5)
except Exception as e:
    print("R5 failed:", str(e)[:80])

# ---- R6 placebo: predict FY2022 crash-risk tercile (should be unrelated) ----
try:
    B6 = BASE.dropna(subset=["ncskew"]).copy()
    B6["hi_crash"] = (B6["ncskew"] > B6["ncskew"].median()).astype(int)
    m6, r6 = run("R6 placebo: high 2022 crash risk ~ controls", "hi_crash", MAIN, B6)
    if r6: rows.append(r6)
except Exception as e:
    print("R6 failed:", str(e)[:80])

# ---- R7 balance ----
print()
print("=== R7 balance on observables (treated vs control) ===")
from scipy import stats
for t in TERMS:
    a = BASE.loc[BASE.abolish_ever == 1, t].dropna()
    b = BASE.loc[BASE.abolish_ever == 0, t].dropna()
    ts, pv = stats.ttest_ind(a, b, equal_var=False)
    smd = (a.mean() - b.mean()) / np.sqrt((a.var() + b.var()) / 2)
    print("  %-13s treated %8.4f  control %8.4f  SMD %+6.3f  t=%+7.2f p=%.4f" %
          (t, a.mean(), b.mean(), smd, ts, pv))

print()
print("=" * 118)
print("ROBUSTNESS SUMMARY (logit unless noted; *** 1%, ** 5%, * 10%)")
print("=" * 118)
tab = pd.DataFrame(rows)
cols = ["test", "N", "events", "pseudoR2", "roa", "logassets_z", "inst", "asy",
        "riskdisc", "esg", "textsim"]
cols = [c for c in cols if c in tab.columns]
print(tab[cols].to_string(index=False))
print()
extras = [c for c in tab.columns if c not in cols]
if extras:
    print("extra terms:")
    print(tab[["test"] + extras].dropna(subset=extras, how="all").to_string(index=False))
tab.to_csv(os.path.join(OUT, "robustness.csv"), index=False, encoding="utf-8-sig")
print("\nsaved: paperA/robustness.csv")
