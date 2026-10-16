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
"""Audit main.tex against the house rules in .claude/skills/paper-edit and
paper-submit. Measures; does not modify.
"""
import re, os

F = os.path.join(MANUSCRIPT, "main.tex")
s = open(F, encoding="utf-8").read()
# strip comments so %% notes are not counted as violations
nc = re.sub(r"(?m)(?<!\\)%.*$", "", s)

# CRediT uses Elsevier's FIXED vocabulary and a fixed "Name: roles" layout, so
# the colons and the en dashes inside it are required, not style slips. Pull it
# out and report it separately instead of counting it as a violation.
_CR = re.compile(
    r"\\section\*\{CRediT[^}]*\}.*?(?=\\section\*|\\bibliographystyle)", re.S)
_m = _CR.search(nc)
CREDIT_COLONS = _m.group(0).count(":") if _m else 0
CREDIT_DASHES = _m.group(0).count("--") if _m else 0
nc = _CR.sub(" ", nc)


def body_of(text):
    """Prose only: cut the preamble and the bibliography block."""
    i = text.find(r"\begin{abstract}")
    j = text.find(r"\bibliographystyle")
    return text[i:j if j > 0 else len(text)]


b = body_of(nc)

print("=" * 74)
print("paper-edit rule check  (main.tex)")
print("=" * 74)

# 1. em/en dashes
em = len(re.findall(r"---", nc))
en = len(re.findall(r"(?<!-)--(?!-)", nc))
print("1. dashes:  '---' = %d   '--' = %d      [rule: none, use commas]" % (em, en))

# 2. colons in prose (exclude math mode, urls, labels, \cite args)
nomath = re.sub(r"\$[^$]*\$", " ", b)
nourl = re.sub(r"\\url\{[^}]*\}", " ", nomath)
noref = re.sub(r"\\(cite[pt]?|ref|label|eqref)\{[^}]*\}", " ", nourl)
colons = re.findall(r"[^.\n]{0,70}:", noref)
print("2. colons in prose: %d                 [rule: none in body text]" % len(colons))
for c in colons[:12]:
    print("      ...%s:" % c.strip()[-66:])

# 3. sentences beginning with a digit
sent = re.split(r"(?<=[.])\s+", re.sub(r"\s+", " ", noref))
dstart = [x for x in sent if re.match(r"^[\d$]", x.strip())]
print("3. sentences starting with a number: %d" % len(dstart))
for x in dstart[:8]:
    print("      %s" % x.strip()[:88])

# 4. \cite not preceded by ~
bad_cite = re.findall(r"(?<!~)(?<![\w{])\\(?:cite[pt]?)\{", nc)
print("4. \\cite without preceding '~': %d     [rule: put ~ before \\cite]" % len(bad_cite))

# 5. hyperref / structure rules
print("5. hyperref loaded in main.tex: %s       [rule: do not double-load]"
      % ("YES" if "\\usepackage{hyperref}" in nc or "hyperref" in nc else "no"))
print("   standalone Acknowledgements section: %s  [rule: none in double-blind]"
      % ("YES" if re.search(r"section\*?\{Acknowledg", nc) else "no"))
print("   standalone Limitations section     : %s  [rule: fold into Discussion]"
      % ("YES" if re.search(r"section\*?\{Limitations", nc) else "no"))

# 6. required-structure sanity
print("   Conclusion sections                : %d  [rule: one short paragraph]"
      % len(re.findall(r"\\section\{Conclusion", nc)))

# 7. abstract length
a = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", nc, re.S)
txt = re.sub(r"\\[a-zA-Z]+\*?|\{|\}|\$|~|\\%", " ", a.group(1))
w = [x for x in txt.split() if any(c.isalnum() for c in x)]
print("7. abstract: %d words                  [house rule 100-150; CJAR allows 250]"
      % len(w))
print()
print("   CRediT block excluded from 1 and 2: %d colons, %d dashes."
      % (CREDIT_COLONS, CREDIT_DASHES))
print("   These are Elsevier's required 'Name: role' format and the official")
print("   role names ('Writing -- original draft'), not prose style slips.")

# 8. bib: proper nouns that BibTeX will lowercase
print()
print("=" * 74)
print("paper-submit rule check  (refs.bib)")
print("=" * 74)
bib = open(os.path.join(MANUSCRIPT, "refs.bib"), encoding="utf-8").read()
entries = re.findall(r"@\w+\{([^,]+),(.*?)\n\}", bib, re.S)
for key, e in entries:
    t = re.search(r"title\s*=\s*\{(.*?)\}\s*,?\s*\n", e, re.S)
    if not t:
        continue
    raw = re.sub(r"\s+", " ", t.group(1)).strip()
    # words that are capitalised in the source but NOT braced -> BibTeX lowercases
    risky = [x for x in re.findall(r"(?<!\{)\b[A-Z][a-z]+\b", raw)
             if x.lower() in {"china", "chinese", "english", "american"}]
    print("  %-18s %s" % (key, "UNBRACED proper noun: %s" % risky if risky else "ok"))
print()
print("  rendered check happens in the PDF: search the References page for")
print("  lowercase 'china'.")
