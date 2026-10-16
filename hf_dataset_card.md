---
license: cc-by-4.0
language:
  - en
  - zh
tags:
  - accounting
  - corporate-governance
  - china
  - supervisory-board
  - audit-committee
  - a-share
  - cninfo
pretty_name: CSBA - China supervisory board abolition
size_categories:
  - 1K<n<10K
configs:
  - config_name: transitions
    data_files: 04_abolition_transitions.csv
  - config_name: announcements
    data_files: 03_abolition_announcements.csv
  - config_name: approval_dates
    data_files: 05_approval_dates.csv
  - config_name: sample_flags
    data_files: 06_sample_flags.csv
---

# CSBA — Board reform and the abolition of the supervisory board

Replication data for the paper **"Board reform and the abolition of the supervisory
board: evidence from China's 2025 governance wave"** by Xiangdong Liu (Jinan
University, ORCID 0000-0002-9438-9285),
Jiahao Chen (Jinan University, ORCID 0000-0003-4673-1311), Zhenyan Liu (University
of Manchester, ORCID 0009-0007-5672-2060) and Jinfeng Pan (Guangdong University of
Finance, ORCID 0009-0008-1950-7465).

Code and documentation: https://github.com/ChenJiahaoJNU/CSBA

## What this is

China's revised Company Law, effective 1 July 2024, lets a listed firm abolish its
supervisory board and vest the statutory oversight functions in the audit
committee of the board. No existing database records the reform, so the transition
file was reconstructed from public CNINFO announcements. Within a single year 2,482
A-share firms announced an abolition.

## Files

| file | rows | what it is |
|------|------|------------|
| `01_cninfo_raw_hits.csv` | 2,674 | raw CNINFO search results before classification |
| `02_classified_candidates.csv` | 2,431 | hits classified as abolition-related |
| `03_abolition_announcements.csv` | 2,522 | the firm's own abolition announcements |
| `04_abolition_transitions.csv` | 2,482 | firm level, first and last announcement, cohort |
| `05_approval_dates.csv` | 2,482 | board proposal date and shareholder approval date |
| `06_sample_flags.csv` | 4,546 | the risk set, public columns only |

### `04_abolition_transitions.csv`

One row per firm that announced an abolition.

| column | meaning |
|--------|---------|
| `secCode` | 6-digit stock code |
| `secName` | firm name as printed in the filing |
| `first_ann`, `last_ann` | first and last abolition announcement dates |
| `n_ann` | number of abolition announcements by that firm |
| `has_charter` | whether the announcement also amends the articles |
| `cohort_month`, `cohort_quarter`, `cohort_year` | derived from `first_ann` |

### `05_approval_dates.csv`

The sweep behind the paper's measurement-error section.

| column | meaning |
|--------|---------|
| `code` | 6-digit stock code |
| `ann` | first abolition announcement, which is the board's proposal |
| `meet` | general meeting date, from the firm's own resolution announcement |
| `n_res` | resolution announcements found in the 180-day window |
| `status` | `ok`, `no_date`, `no_orgid`, `query_fail`, `worker_error` |

2,377 of 2,482 resolved. Median gap 102 days, interquartile range 21 to 147. Only
**35.7 per cent** of firms vote in the same calendar quarter as their proposal,
which is why the paper makes no timing claim.

### `06_sample_flags.csv`

The 4,546-firm risk set with the licensed covariates stripped out. 2,072 firms
abolished, or 45.6 per cent, which is the figure the paper reports.

## Licence and what is deliberately absent

Everything here was reconstructed from **public CNINFO disclosures**. A-share
filings are public documents, and this data is released under CC BY 4.0.

The paper's explanatory variables come from a commercial vendor, whose licence
permits use for replication but **not redistribution**. They are therefore not
included. That covers return on assets, leverage, total assets, institutional
ownership, information asymmetry, risk-disclosure intensity, the CNRDS ESG rating,
MD&A text similarity, analyst coverage, stock-price crash risk and audit opinion.
Obtain them under your own licence; the pipeline in the code repository reads them
from a `vendor/` folder.

You can reproduce the transition file, the sample construction counts, the cohort
distribution and the approval-date analysis from this data alone.

## Known limitations, stated by the authors

- **The treatment date is the board's proposal, not the shareholder vote.** Across
  all 2,482 firms the two differ by a median of 102 days.
- **The approval-date extraction is automated and unvalidated by hand.** Nine of
  2,377 resolved firms (0.4 per cent) yield an impossible negative gap, so the file
  is sound distributionally and **not firm-by-firm**. Do not quote an individual
  firm's gap without checking that firm's filing.
- **Keyword recall is imperfect.** A single-phrase query would have missed 193
  genuine announcements; this release uses a nine-keyword union.
- **The information-asymmetry result does not reproduce with alternative proxies**
  (crash risk, analyst coverage, |ROA − CFO|). The paper reports this as a failure.

## Citation

If you use this data, please cite the paper, and this dataset:

```
Liu, X., Chen, J., Liu, Z., and Pan, J. Board reform and the abolition of the
supervisory board: evidence from China's 2025 governance wave. China Journal of
Accounting Research, forthcoming.
```

```
@misc{csba2026,
  title  = {Board reform and the abolition of the supervisory board: evidence from
            China's 2025 governance wave},
  author = {Liu, Xiangdong and Chen, Jiahao and Liu, Zhenyan and Pan, Jinfeng},
  year   = {2026},
  url    = {https://huggingface.co/datasets/Changahou/CSBA}
}
```
