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
"""Paper A: build the estimation sample and run baseline regressions.

Design
------
Risk set   : firms present in the panel in FY2023 (the last pre-reform year).
Treatment  : abolition of the supervisory board (监事会), effective 2024-07-01 law.
DV options : (a) abolish_ever  -- binary, abolished by 2025-12-31
             (b) cohort_quarter -- ordered timing
Covariates : measured at FY2022 (pre-determined w.r.t. the 2025 wave), plus
             three-year averages where noted.
"""
import os
import numpy as np
import pandas as pd

DATA = VENDOR_DATA
SB = DATA
os.makedirs(OUT, exist_ok=True)


def load(fn, cols=None):
    d = pd.read_stata(os.path.join(DATA, fn))
    d.columns = [c.strip().lower() for c in d.columns]
    d["stkcd"] = pd.to_numeric(d["stkcd"], errors="coerce").astype("Int64")
    d["year"] = pd.to_numeric(d["year"], errors="coerce").astype("Int64")
    if cols:
        d = d[["stkcd", "year"] + [c for c in cols if c in d.columns]]
    return d.dropna(subset=["stkcd", "year"])


# ---------------- risk set: FY2023 universe with covariates ----------------
fbi = load("2000-2023_Firm_Basic_Info.dta")
base = fbi[fbi.year == 2023][["stkcd", "year", "firmname", "industryname",
                              "industrycode", "provincename", "provincecode"]].copy()
print("FY2023 universe: %d firms" % len(base))

BLOCKS = [("2000-2023_ROA.dta", ["roa"]),
          ("2000-2023_Leverage.dta", ["leverage"]),
          ("2000-2023_Total_Assets.dta", ["assets"]),
          ("2000-2023_Institutional_Ownership.dta", ["institution"]),
          ("2007-2023_Information_Asymmetry.dta", ["asy"]),
          ("2007-2023_Risk_Disclosure.dta", ["riskdisclosure"]),
          ("2007-2023_CNRDS_ESG_Rating.dta", ["esg"]),
          ("2010-2023_MDA_Text_Similarity.dta", ["textsimilarity"]),
          ("2001-2023_Analyst_Coverage.dta", ["analystcoverage"]),
          ("2000-2023_Stock_Price_Crash_Risk.dta", ["ncskew", "duvol"]),
          ("2000-2023_Audit_Opinion.dta", ["auditopinion"])]

s23 = base.copy()
for fn, cols in BLOCKS:
    d = load(fn, cols)
    s23 = s23.merge(d[d.year == 2023][["stkcd"] + cols], on="stkcd", how="left",
                    suffixes=("", "_y23"))
print("after merging FY2023 covariates: %d firms, %d with roa" %
      (len(s23), s23.roa.notna().sum()))

# FY2022 covariates (pre-determination)
p22 = None
for fn, cols in BLOCKS:
    d = load(fn, cols)
    d = d[d.year == 2022][["stkcd"] + cols]
    p22 = d if p22 is None else p22.merge(d, on="stkcd", how="outer")

panel = s23.merge(p22, on="stkcd", how="left", suffixes=("_y23", "_y22"))

# ---------------- treatment ----------------
tab = pd.read_csv(os.path.join(SB, "abolition_transitions.csv"))
tab["stkcd"] = pd.to_numeric(tab["secCode"], errors="coerce").astype("Int64")
panel = panel.merge(tab[["stkcd", "first_ann", "cohort_quarter", "cohort_month"]],
                    on="stkcd", how="left")
panel["abolish_ever"] = panel["first_ann"].notna().astype(int)
print()
print("treated among FY2023 universe: %d (%.1f%%)" %
      (panel.abolish_ever.sum(), 100 * panel.abolish_ever.mean()))

# ---------------- derived variables ----------------
# NOTE: merging FY2023 and FY2022 blocks produced suffixed columns (_y23/_y22),
# so every covariate must be referenced with its suffix.
panel["logassets"] = np.log(panel["assets_y22"].where(panel["assets_y22"] > 0))
panel["mao_lag"] = np.where(panel["auditopinion_y22"].isna(), np.nan,
                            (panel["auditopinion_y22"] == 0).astype(float))
print("logassets non-missing: %d ; mao_lag non-missing: %d" %
      (panel.logassets.notna().sum(), panel.mao_lag.notna().sum()))


def winsor(s, lo=0.01, hi=0.99):
    if s.notna().sum() == 0:
        return s
    return s.clip(s.quantile(lo), s.quantile(hi))


for c in ["roa", "leverage", "institution", "asy", "riskdisclosure", "esg",
          "textsimilarity", "analystcoverage", "ncskew", "duvol"]:
    if c + "_y22" in panel.columns:
        panel[c + "_y22_w"] = winsor(panel[c + "_y22"])
panel["analyst_log"] = np.log1p(panel["analystcoverage_y22_w"])

# quarterly cohort as an ordinal (0 = never)
QMAP = {"2025Q1": 1, "2025Q2": 2, "2025Q3": 3, "2025Q4": 4, "2026Q1": 5, "2026Q2": 6}
panel["cohort_ord"] = panel["cohort_quarter"].map(QMAP).fillna(0).astype(int)

panel.to_stata(os.path.join(OUT, "paperA_estimation.dta"), write_index=False,
               version=118)
print("saved: paperA/paperA_estimation.dta  %s" % (panel.shape,))

# ---------------- descriptives ----------------
VARS = ["abolish_ever", "roa_y22_w", "leverage_y22_w", "logassets",
        "institution_y22_w", "asy_y22_w", "riskdisclosure_y22_w", "esg_y22_w",
        "textsimilarity_y22_w", "analyst_log", "ncskew_y22_w"]
VARS = [v for v in VARS if v in panel.columns]
print()
print("=== descriptives (FY2022 covariates) ===")
d = panel[VARS].describe(percentiles=[.25, .5, .75]).T
d["missing%"] = 100 * panel[VARS].isna().mean()
print(d[["count", "mean", "std", "min", "50%", "max", "missing%"]].round(4).to_string())

# ---------------- raw differences: treated vs not ----------------
print()
print("=== univariate: treated vs not (FY2022) ===")
comp = panel.groupby("abolish_ever")[VARS[1:]].mean().T
comp.columns = ["not_abolished", "abolished"]
comp["diff"] = comp["abolished"] - comp["not_abolished"]
print(comp.round(4).to_string())
comp.to_csv(os.path.join(OUT, "univariate.csv"), encoding="utf-8-sig")
