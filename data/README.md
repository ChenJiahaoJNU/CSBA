# Data

Everything here was reconstructed from **public CNINFO disclosures**. A-share
filings are public documents, so these files may be redistributed. Nothing derived
from the commercial vendor is included.

| file | rows | what it is |
|------|------|------------|
| `01_cninfo_raw_hits.csv` | 2,674 | raw CNINFO search results before classification |
| `02_classified_candidates.csv` | 2,431 | hits classified as abolition-related |
| `03_abolition_announcements.csv` | 2,522 | the firm's own abolition announcements |
| `04_abolition_transitions.csv` | 2,482 | firm-level: first and last announcement, cohort |
| `05_approval_dates.csv` | 2,482 | board proposal date and shareholder-approval date |
| `06_sample_flags.csv` | 4,546 | the risk set with public columns only |

## Column notes

**`04_abolition_transitions.csv`** — one row per firm that announced an abolition.

| column | meaning |
|--------|---------|
| `secCode` | 6-digit stock code |
| `secName` | firm name as printed in the filing |
| `first_ann` / `last_ann` | first and last abolition announcement dates |
| `n_ann` | number of abolition announcements by that firm |
| `has_charter` | whether the announcement also amends the articles |
| `cohort_month`, `cohort_quarter`, `cohort_year` | from `first_ann` |

**`05_approval_dates.csv`** — the sweep behind the paper's measurement-error
section.

| column | meaning |
|--------|---------|
| `code` | 6-digit stock code |
| `ann` | first abolition announcement (the board's proposal) |
| `meet` | general-meeting date, from the firm's own resolution announcement |
| `n_res` | resolution announcements found in the 180-day window |
| `status` | `ok`, `no_date`, `no_orgid`, `query_fail`, `worker_error` |

2,377 of 2,482 resolved. Median gap 102 days, interquartile range 21 to 147. Only
**35.7 per cent** of firms vote in the same calendar quarter as their proposal.

> **Do not quote a gap for an individual firm.** Nine firms (0.4 per cent) yield an
> impossible negative gap, which means the automated date extraction picks up the
> wrong date for some firms, almost certainly a *previous* meeting. The file is
> sound distributionally and not firm-by-firm. Hand-check the PDF before citing any
> single row.

**`06_sample_flags.csv`** — the 4,546-firm risk set, with the licensed covariates
stripped out. Columns: `stkcd`, `abolish_ever`, `cohort_quarter`, `cohort_month`,
`first_ann`, `industrycode`, `provincename`, `year`. 2,072 firms abolished (45.6 per
cent), which is the number the paper reports.

## What is NOT here

The vendor's licence permits use for replication but not redistribution. These must
be obtained under your own licence:

return on assets · leverage · total assets · institutional ownership · information
asymmetry · risk-disclosure intensity · CNRDS ESG rating · MD&A text similarity ·
analyst coverage · stock-price crash risk (`ncskew`, `duvol`) · audit opinion

Place them under `vendor/` as described in `../code/README.md`. The regression
scripts read single-variable `.dta` blocks from `vendor/data/` and merged panels
from `vendor/panel/`.

## Search keywords

The union of nine title keywords produced the raw hits. Recall is imperfect. A
single-phrase query using only `quxiao jianshihui` would have missed 193 genuine
announcements worded `quxiao gongsi jianshihui`, and the phrase a researcher would
naturally reach for, `shenji weiyuanhui xingshi jianshihui zhiquan`, returns zero
filings because firms do not use it.
