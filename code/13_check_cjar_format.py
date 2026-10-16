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
"""Check the manuscript against CJAR's hard formatting limits."""
import re

s = open(os.path.join(MANUSCRIPT, "main.tex"), encoding="utf-8").read()

# Strip LaTeX comments first. Without this, a leftover %% note can satisfy a
# required-section pattern and produce a false "present" (this happened once:
# a stale comment mentioning the GenAI declaration matched the GenAI check
# long after the actual section had been deleted).
s_nc = re.sub(r"(?m)(?<!\\)%.*$", "", s)

a = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", s, re.S)
if a:
    txt = re.sub(r"\\[a-zA-Z]+\*?|\{|\}|\$|~|\\%", " ", a.group(1))
    words = [x for x in txt.split() if any(c.isalnum() for c in x)]
    print("abstract words = %d   (limit 250)  -> %s" %
          (len(words), "OK" if len(words) <= 250 else "OVER"))

h = re.search(r"\\begin\{highlights\}(.*?)\\end\{highlights\}", s, re.S)
if h:
    items = re.findall(r"\\item\s+(.*)", h.group(1))
    print("highlights: %d bullets (need 3-5) -> %s" %
          (len(items), "OK" if 3 <= len(items) <= 5 else "FIX"))
    for it in items:
        t = re.sub(r"\\[a-zA-Z]+\*?|\{|\}|\$|~|\\%", "", it).strip()
        print("   %3d chars %s  %s" % (len(t), "OK " if len(t) <= 85 else "OVER", t))

k = re.search(r"\\begin\{keyword\}(.*?)\\end\{keyword\}", s, re.S)
if k:
    ks = [x.strip() for x in k.group(1).split(r"\sep") if x.strip()]
    print("keywords: %d (need 1-6) -> %s" % (len(ks), ks))

print()
print("--- other required items ---")
for label, pat in (("Declaration of competing interest", r"Declaration of competing"),
                   ("Data availability", r"Data availability"),
                   ("Funding statement", r"Funding|funding agenc|specific grant")):
    print("  %-34s %s" % (label, "present" if re.search(pat, s_nc) else "MISSING"))
print("  %-34s %s" % ("Declaration of generative AI",
                      "present" if re.search(r"generative AI|GenAI", s_nc)
                      else "absent (author decision - CJAR may require it)"))
print("  %-34s %s" % ("author-year citation mode",
                      "authoryear" if "authoryear" in s_nc else "numbered"))
print("  %-34s %s" % ("bibliographystyle",
                      re.search(r"\\bibliographystyle\{([^}]+)\}", s_nc).group(1)))

# A blind manuscript must not leak the author block.
if re.search(r"\\blindtrue", s_nc):
    leak = re.search(r"\\author\{(.*?)\}", s_nc, re.S)
    body = leak.group(1).strip() if leak else ""
    print("  %-34s %s" % ("[blind] author block empty",
                          "OK" if body == "" else "LEAK -> %r" % body[:60]))

# Checking \author{} alone is NOT enough. Author names can reach a supposedly
# anonymized manuscript through any other section. That actually happened: a
# CRediT statement naming all four authors was added to main.tex and sailed past
# a green "author block empty" tick. So scan the RENDERED PDF, which is what a
# reviewer actually receives.
import os
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

BLOCKED = ["Xiangdong", "Jiahao", "Zhenyan", "Jinfeng",
           "Jinan", "Manchester", "Guangdong",
           "tliuxd", "changahou", "ppjinfeng", "3348156367",
           "0000-0002", "0009-0008", "2025CXY324",
           "Author Name", "author@example", "PENDING"]

pdf = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.pdf")
if PdfReader is None:
    print("  %-34s pypdf not installed, SKIPPED" % "[blind] rendered-PDF scan")
elif not os.path.exists(pdf):
    print("  %-34s main.pdf missing, SKIPPED" % "[blind] rendered-PDF scan")
else:
    _r = PdfReader(pdf)
    _t = "".join((p.extract_text() or "") for p in _r.pages)
    hits = [w for w in BLOCKED if w in _t]
    print("  %-34s %s" % ("[blind] rendered-PDF scan",
                          "clean" if not hits else "LEAK -> %s" % hits))
    au = (_r.metadata or {}).get("/Author")
    print("  %-34s %s" % ("[blind] PDF /Author empty",
                          "OK" if not (au or "").strip() else "LEAK -> %r" % au))
