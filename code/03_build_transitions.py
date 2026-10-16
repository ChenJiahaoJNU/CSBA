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
"""Derive the supervisory-board abolition transition table.

Corrections applied vs the first pass:
  * the abolition phrase allows an inserted 公司/本公司 (取消公司监事会), which the
    first regex missed -- that residue was 193 real announcements, not noise;
  * distinguish the BOARD PROPOSAL from the SHAREHOLDER-MEETING APPROVAL. The legal
    act is the shareholder resolution, so the treatment date must come from the
    股东会/股东大会 resolution announcement, not the board proposal.
"""
import os, re
import pandas as pd

OUT = DATA
raw = pd.read_csv(os.path.join(OUT, "sb_announcements_raw.csv")).drop_duplicates("announcementId")

INTERMEDIARY = ("受托管理|信用评级|评级报告|募集说明书|保荐|持续督导|独立财务顾问|"
                "督导|受托管理事务")
INTERM = raw.title.str.contains(INTERMEDIARY, na=False)

# abolition phrase, allowing an inserted 公司/本公司 and optional 设置
ABOL = (r"取消(?:本?公司)?(?:设置)?监事会|不再设(?:置)?(?:本?公司)?监事会|"
        r"撤销(?:本?公司)?监事会|不设(?:置)?(?:本?公司)?监事会|"
        r"废止(?:本?公司)?监事会|"
        r"取消(?:本?公司)?监事|不再设(?:置)?监事")

own = raw[raw.title.str.contains(ABOL, na=False) & ~INTERM].copy()
print("firm's own abolition announcements: %d  (firms %d)" %
      (len(own), own.secCode.nunique()))

# ---- classify by the decision body -------------------------------------------
approval = own.title.str.contains("股东会|股东大会", na=False) & \
           own.title.str.contains("决议|批准|通过|审议通过", na=False)
proposal = own.title.str.contains("董事会|监事会决议|第.届董事会", na=False)
charter = own.title.str.contains("章程", na=False)

own["is_approval"] = approval
own["is_proposal"] = proposal
own["has_charter"] = charter
print()
print("=== classification ===")
print("  mentions shareholder-meeting resolution : %d" % approval.sum())
print("  mentions board resolution               : %d" % proposal.sum())
print("  mentions 章程                           : %d (%.0f%%)" %
      (charter.sum(), 100 * charter.mean()))
print("  neither (bare abolition notice)         : %d" % (~approval & ~proposal).sum())

own = own.sort_values(["secCode", "date"])
g = own.groupby("secCode")
tab = pd.DataFrame({
    "secName": g.secName.first(),
    "first_ann": g.date.min(),
    "last_ann": g.date.max(),
    "n_ann": g.size(),
    "has_charter": g.has_charter.max(),
    "has_approval_ann": g.is_approval.max(),
}).reset_index()
# treatment date = first shareholder-approval announcement if any, else first notice
first_app = own[own.is_approval].groupby("secCode").date.min()
tab["approval_date"] = tab.secCode.map(first_app)
tab["treat_date"] = tab.approval_date.fillna(tab.first_ann)

tab["treat_year"] = tab.treat_date.str[:4].astype(int)
print()
print("=== treatment cohort by year (treat_date) ===")
print(tab.treat_year.value_counts().sort_index().to_string())
print()
print("=== how many firms have a shareholder-meeting approval announcement? ===")
print("  %d of %d (%.0f%%)" % (tab.has_approval_ann.sum(), len(tab),
                              100 * tab.has_approval_ann.mean()))

tab.to_csv(os.path.join(OUT, "abolition_transitions.csv"), index=False,
           encoding="utf-8-sig")
own.to_csv(os.path.join(OUT, "abolition_announcements.csv"), index=False,
           encoding="utf-8-sig")
print("\nsaved:")
print("  sb/abolition_transitions.csv   %d firms" % len(tab))
print("  sb/abolition_announcements.csv %d announcements" % len(own))

# ---- sanity: overlap with the panel's firm universe ----
try:
    fbi = pd.read_stata(os.path.join(VENDOR_DATA, "2000-2023_Firm_Basic_Info.dta"))
    fbi.columns = [c.lower() for c in fbi.columns]
    universe = set(pd.to_numeric(fbi.stkcd, errors="coerce").dropna().astype(int))
    hit = set(pd.to_numeric(tab.secCode, errors="coerce").dropna().astype(int)) & universe
    print()
    print("=== overlap with the panel universe ===")
    print("  panel firms (2000-2023)      : %d" % len(universe))
    print("  abolition firms matched      : %d of %d (%.0f%%)" %
          (len(hit), len(tab), 100 * len(hit) / len(tab)))
except Exception as e:
    print("panel overlap check skipped:", e)
