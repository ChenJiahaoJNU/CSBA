# Replication package

**Board reform and the abolition of China's supervisory board**
(short title `CSBA`)

Xiangdong Liu (Jinan University), Jiahao Chen (Jinan University),
Zhenyan Liu (University of Manchester), Jinfeng Pan (Guangdong University of Finance)

## Where this lives

| | |
|---|---|
| Code and documentation | https://github.com/ChenJiahaoJNU/CSBA |
| Data | https://huggingface.co/datasets/Changahou/CSBA |

The data files are mirrored in this repository so that a clone is self-contained.
Both locations carry the same public data, and the HuggingFace copy exists so the
dataset can be cited and versioned independently of the code.

> **Note for the anonymized manuscript.** Both URLs contain an author-identifying
> account name. They therefore appear on the **title page only** and are
> deliberately absent from `main.tex`. Never paste either link into the
> double-anonymized manuscript.

---

## What this paper does

China's revised Company Law, effective 1 July 2024, lets a listed firm abolish its
supervisory board and vest the statutory oversight functions in the audit
committee. No existing database records the reform, so we reconstruct the
transition file from public CNINFO filings and ask which firms gave up the
independent monitor.

Headline result: the firms that moved were larger, more profitable, more
institutionally held, more forthcoming on risk and higher-rated on ESG, and the
strongest single predictor is **higher** information asymmetry. We also report a
timing result that **does not survive** our own testing, and we say so in the paper.

---

## Layout

```
replication/
  README.md          this file
  code/              pipeline scripts, path-relocatable
  data/              ONLY data reconstructed from public filings
  output/            created at run time
  manuscript/        optional copy of the LaTeX sources
  vendor/            YOU create this; licensed inputs, not shipped
```

## The licence boundary (read this first)

The package is split deliberately in two, and the split is not cosmetic.

**`data/` is redistributable.** Everything in it was reconstructed from public
CNINFO disclosures. A-share filings are public documents.

**`vendor/` is not, and is not included.** The explanatory variables come from a
commercial vendor, and its licence permits use for replication but not
redistribution. That covers return on assets, leverage, total assets,
institutional ownership, information asymmetry, risk-disclosure intensity, the
CNRDS ESG rating, MD&A text similarity, analyst coverage, stock-price crash risk
and audit opinion.

If you want to reproduce the regression results, you must obtain equivalent
variables under your own licence and place them in `vendor/`. The scripts fail
loudly rather than substituting anything. **You can reproduce the transition file,
the sample construction counts, the cohort distribution and the approval-date
analysis with `data/` alone.**

## Running it

```bash
pip install pandas numpy statsmodels scipy pypdf

export PAPER_A_VENDOR=/path/to/your/licensed/inputs   # optional for steps 1-5
export PAPER_A_OUT=/path/to/outputs                   # optional

cd code
python 01_harvest_cninfo.py        # or 01b_..., which is resumable
python 02_classify_candidates.py
python 03_build_transitions.py
...
```

Steps 1, 2, 4, 10, 13 and 14 need no licensed input at all. Steps 3, 5, 6, 7, 8,
9, 11 and 12 do; each says so in the table in `code/README.md`.

Step 01 hits CNINFO over the network and takes a while. `01b_...` is the resumable
version that wrote the file shipped here, and it skips firms already done.

## Environment this was produced with

Python 3.12, pandas 2.2.2, numpy 1.26.4, statsmodels, pypdf 6.20.1, and TeX Live
2022 for the manuscript. Set `PYTHONNOUSERSITE=1` if your machine has more than one
numpy installed.

## What we know is imperfect

We would rather you hear these from us than find them yourself.

- **The treatment date is the board's proposal, not the shareholder vote.** Across
  all 2,482 firms the two differ by a median of 102 days, and only 35.7 per cent
  vote in the same calendar quarter. That is why the paper makes no timing claim.
- **The approval-date extraction is automated and unvalidated by hand.** Nine of
  2,377 resolved firms (0.4 per cent) yield an impossible negative gap. The measure
  is usable at the distributional level and **must not be quoted for an individual
  firm** without checking that firm's PDF.
- **The keyword search has imperfect recall.** A single-phrase query would have
  missed 193 genuine announcements. The nine-keyword union is what we shipped.
- **The information-asymmetry result does not reproduce with alternative proxies**
  (crash risk, analyst coverage, |ROA − CFO|). The paper reports this as a failure.
- **Governance covariates are absent.** Board size, independent-director share,
  audit-committee composition and state ownership are not in the model, and
  institutional ownership is the covariate on which treated and control firms
  differ most (standardised mean difference 0.301). Any causal reading has to
  address that, and the paper says so.

## Data availability

The transition file contains only firm identifiers, announcement dates and titles
taken from public filings, and is shared freely. The licensed firm-year variables
cannot be redistributed. `data/README.md` documents every file and column.
