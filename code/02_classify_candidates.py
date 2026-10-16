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
"""Analyse the harvested announcements and derive the abolition-date table.

Step 1: understand what is in there (title patterns, contamination).
Step 2: classify into firm's-own abolition announcements vs noise.
Step 3: emit firm -> abolition date.
"""
import os, re
import pandas as pd

OUT = DATA
raw = pd.read_csv(os.path.join(OUT, "sb_announcements_raw.csv"))
raw = raw.drop_duplicates("announcementId")
print("raw unique announcements: %d" % len(raw))
print("distinct secCode          : %d" % raw.secCode.nunique())
print("date range                : %s .. %s" % (raw.date.min(), raw.date.max()))
print()
print("=== by matched_key ===")
print(raw.matched_key.value_counts().to_string())

# ---- contamination: third-party documents that merely mention the event ----
NOISE = ["受托管理", "受托管理事务报告", "信用评级", "评级报告", "债券", "募集说明书",
         "法律意见书", "律师", "保荐", "持续督导", "独立财务顾问", "督导"]
mask_noise = raw.title.str.contains("|".join(NOISE), na=False)
print()
print("=== third-party / intermediary documents (to EXCLUDE) ===")
print("  count: %d" % mask_noise.sum())
for t in raw.loc[mask_noise, "title"].head(8):
    print("   -", t[:78])

# ---- the firm's own abolition announcement ----
ABOL = r"取消监事会|不再设(?:置)?监事会|撤销监事会|不设监事会|废止监事会|取消设置监事会|不再设置监事"
mask_abol = raw.title.str.contains(ABOL, na=False)
print()
print("=== titles matching an abolition phrase ===")
print("  count: %d" % mask_abol.sum())

keep = raw[mask_abol & ~mask_noise].copy()
print("  after dropping intermediary docs: %d announcements, %d firms" %
      (len(keep), keep.secCode.nunique()))

print()
print("=== sample of the firm's own abolition titles ===")
for t in keep.title.drop_duplicates().head(18):
    print("   -", t[:88])

# ---- do the titles that DON'T match still matter? sample the residue ----
resid = raw[~mask_abol & ~mask_noise]
print()
print("=== residue (matched a keyword but not an abolition phrase): %d ===" % len(resid))
for t in resid.title.drop_duplicates().head(10):
    print("   -", t[:88])

# ---- how does the abolition announcement relate to 章程修订? ----
has_charter = keep.title.str.contains("章程")
print()
print("=== within the abolition set, does the title mention 章程修订? ===")
print("  yes: %d   no: %d" % (has_charter.sum(), (~has_charter).sum()))

keep.to_csv(os.path.join(OUT, "abolition_candidates.csv"),
            index=False, encoding="utf-8-sig")
print("\nsaved: sb/abolition_candidates.csv  (%d rows)" % len(keep))
