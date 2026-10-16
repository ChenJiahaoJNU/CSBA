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
"""Finalise the abolition transition asset with monthly cohorts."""
import os
import pandas as pd

OUT = DATA
own = pd.read_csv(os.path.join(OUT, "abolition_announcements.csv"))
own["date"] = pd.to_datetime(own["date"])
own["secCode"] = pd.to_numeric(own["secCode"], errors="coerce").astype("Int64")

g = own.sort_values("date").groupby("secCode")
tab = pd.DataFrame({
    "secName": g.secName.first(),
    "first_ann": g.date.min(),
    "last_ann": g.date.max(),
    "n_ann": g.size(),
    "has_charter": g.title.apply(lambda s: s.str.contains("章程").any()),
}).reset_index()
tab["cohort_month"] = tab.first_ann.dt.strftime("%Y-%m")
tab["cohort_quarter"] = tab.first_ann.dt.to_period("Q").astype(str)
tab["cohort_year"] = tab.first_ann.dt.year

# first announcement is usually the BOARD PROPOSAL; the shareholder meeting follows.
# Record the gap explicitly as a data limitation rather than hiding it.
tab = tab.sort_values("first_ann")
tab.to_csv(os.path.join(OUT, "abolition_transitions.csv"), index=False,
           encoding="utf-8-sig")

print("abolition firms: %d" % len(tab))
print()
print("=== cohort by quarter ===")
print(tab.cohort_quarter.value_counts().sort_index().to_string())
print()
print("=== panel overlap ===")
fbi = pd.read_stata(os.path.join(VENDOR_DATA, "2000-2023_Firm_Basic_Info.dta"))
fbi.columns = [c.lower() for c in fbi.columns]
uni = set(pd.to_numeric(fbi.stkcd, errors="coerce").dropna().astype(int))
codes = set(tab.secCode.dropna().astype(int))
print("  in panel universe : %d of %d (%.0f%%)" % (len(codes & uni), len(codes),
                                                   100 * len(codes & uni) / len(codes)))
print("  NOT in panel      : %d" % len(codes - uni))
print()
print("=== how many panel firms did NOT abolish (the control pool) ===")
print("  %d" % len(uni - codes))
print()
print("saved: sb/abolition_transitions.csv")
print(tab.head(6).to_string(index=False))
