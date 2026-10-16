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
"""Refine: (a) how many titles mention a shareholder meeting at all,
(b) the monthly shape of the wave, (c) is the 2024 cohort really empty?
"""
import os
import pandas as pd

OUT = DATA
own = pd.read_csv(os.path.join(OUT, "abolition_announcements.csv"))
raw = pd.read_csv(os.path.join(OUT, "sb_announcements_raw.csv"))

print("announcements: %d   firms: %d" % (len(own), own.secCode.nunique()))
print()
print("=== title contains 股东会/股东大会 (relaxed) ===")
m = own.title.str.contains("股东会|股东大会", na=False)
print("  %d of %d (%.0f%%)" % (m.sum(), len(own), 100 * m.mean()))
for t in own.loc[m, "title"].head(6):
    print("   -", t[:80])
print()
print("=== title contains 董事会 ===")
mb = own.title.str.contains("董事会", na=False)
print("  %d (%.0f%%)" % (mb.sum(), 100 * mb.mean()))

print()
print("=== monthly shape of first announcement ===")
own["ym"] = own.date.str[:7]
first = own.sort_values("date").groupby("secCode").date.min()
fm = first.str[:7].value_counts().sort_index()
for k, v in fm.items():
    print("  %s  %4d  %s" % (k, v, "#" * int(v / 25)))

print()
print("=== is the 2024 cohort empty in the RAW file too? ===")
raw["ym"] = raw.date.str[:7]
r24 = raw[raw.date < "2025-01-01"]
print("  raw announcements dated before 2025: %d" % len(r24))
print("  of those, how many are intermediary docs: %d" %
      r24.title.str.contains("受托管理|信用评级|保荐|督导", na=False).sum())
print("  sample titles from 2024:")
for t in r24.title.drop_duplicates().head(10):
    print("   -", t[:84])

print()
print("=== earliest abolition announcements per firm (first 12 firms) ===")
f = own.sort_values("date").groupby("secCode").first().reset_index()
for _, r in f.head(12).iterrows():
    print("  %-8s %-10s %s" % (r.secCode, r.date, str(r.title)[:62]))
