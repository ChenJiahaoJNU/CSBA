# Pipeline

Run in the numbered order. `config.py` holds every path; override with the
environment variables `PAPER_A_DATA`, `PAPER_A_VENDOR`, `PAPER_A_OUT`,
`PAPER_A_MANUSCRIPT` rather than editing tracked code.

| # | script | reads | writes | licensed input? |
|---|--------|-------|--------|-----------------|
| 01 | `01_harvest_cninfo.py` | CNINFO (network) | `01_cninfo_raw_hits.csv` | no |
| 01b | `01b_harvest_cninfo_resumable.py` | CNINFO (network) | same, resumable | no |
| 02 | `02_classify_candidates.py` | 01 | `02_classified_candidates.csv` | no |
| 03 | `03_build_transitions.py` | 01 | `03_...`, `04_...` | yes, firm basic info |
| 04 | `04_refine_announcements.py` | 03, 01 | refined announcements | no |
| 05 | `05_final_transitions.py` | 03 | `04_abolition_transitions.csv` | yes, firm basic info |
| 06 | `06_build_estimation_file.py` | 04, 05 + panel | `paperA_estimation.dta` | yes, all covariates |
| 07 | `07_main_regressions.py` | 06 | Table 3, Table 4 | yes |
| 08 | `08_robustness.py` | 06 + panel | Table 5 | yes |
| 09 | `09_cohort_ordering_fix.py` | 06 | cohort re-coding, ordered logit | yes |
| 10 | `10_approval_dates_sweep.py` | 03, CNINFO (network) | `05_approval_dates.csv` | no |
| 11 | `11_gap_analysis_recoding.py` | 06, 10 | gap distribution, re-coded cohorts | yes |
| 12 | `12_withinwave_cuts.py` | 06, 10 | within-wave cuts | yes |
| 13 | `13_check_cjar_format.py` | manuscript | pass/fail on CJAR limits | no |
| 14 | `14_check_house_style.py` | manuscript, bib | pass/fail on house style | no |

## The two steps worth understanding

**Step 09 exists because of a bug we found and fixed.** The cohort variable in the
estimation file is coded `0 = never abolished, 1..4 = 2025Q1..Q4`. In an ordered
logit the categories must be ordered by the underlying construct, and "never" is
the *latest* state, not the earliest. The original coding therefore put
never-adopters at the bottom and made the signs read backwards. Step 09 re-codes to
`1..4 = 2025Q1..Q4, 5 = 2026, 6 = never` and re-estimates. The paper reports the
corrected reading, and reports that the timing result does not survive either way.

**Step 10 is the reason the paper abandons its timing claim.** It resolves each
firm's own general-meeting resolution announcement and measures the gap from the
board's proposal. Only 35.7 per cent of firms vote in the same quarter as their
proposal, so the quarterly cohort is mis-assigned for about two-thirds of firms.
Step 12 then shows the within-wave coefficient **changes sign** with the cohort
definition on the same 1,397 firms, which is the clearest reason not to claim a
timing result.

## Quirks that will otherwise cost you an afternoon

- **CNINFO's `stock` parameter needs `code,orgId`.** Passing a bare code returns
  zero hits silently rather than an error. `10_approval_dates_sweep.py` resolves
  the `orgId` through `topSearch/query` first.
- **Dates must be read from the general-meeting resolution, not the abolition
  notice.** The notice is the board's proposal and the meeting has not happened
  yet, so reading dates from it yields impossible negative gaps.
- **`auditopinion` is coded `0 = modified, 1 = standard`** in the vendor file, so
  `mao = 1[auditopinion == 0]`.
- **`2000-2023F1_Stock_Price_Crash_Risk.dta` is the t+1 lead**, not the
  contemporaneous year. A predictive design must use it and loses a year.
- **Chinese text cannot pass through PowerShell quoting.** Write a `.py` file.
- **The `.bib` must keep field values ASCII.** CJK inside a field aborts the second
  pdflatex pass. Braced comments are fine; braces around proper nouns (`{C}hina`)
  are required because BibTeX's `change.case$` lowercases unbraced capitals.
