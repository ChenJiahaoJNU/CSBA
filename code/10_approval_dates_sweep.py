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
"""Proposal -> shareholder-approval gap for ALL abolition firms (resumable).

Why: the treatment date in Paper A is the first announcement, which is the
BOARD PROPOSAL, not the shareholder approval. A 30-firm check found a 7-177 day
gap (median 100), which is why cohorts are read at quarterly level or coarser.
This script measures the gap for the full set so the caveat can be stated as a
distribution over all firms rather than a 30-firm sample.

Resumable: progress is written to datecheck/gap_full.csv every FLUSH firms; on
restart, firms already present are skipped. PDFs are parsed in memory (no disk
bloat: the 30-firm run wrote ~2500 files' worth of space otherwise).
"""
import io, json, os, re, threading, time, urllib.parse, urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from pypdf import PdfReader

SB = DATA
OUT = os.path.join(OUT, "datecheck")
os.makedirs(OUT, exist_ok=True)
PROG = os.path.join(OUT, "gap_full.csv")
FLUSH = 25
WORKERS = 5

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
      "Referer": "http://www.cninfo.com.cn/new/commonUrl?url=disclosure/list/notice"}
TOP = "http://www.cninfo.com.cn/new/information/topSearch/query"
API = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
DATE = re.compile(r"(20\d{2})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日")
COLS = ["code", "ann", "meet", "n_res", "status"]


def post(url, data, timeout=45, tries=3):
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(
                url, data=urllib.parse.urlencode(data).encode(), headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:
            last = e
            time.sleep(1.5 * (k + 1))
    raise last


_CACHE = {}
_CACHE_LOCK = threading.Lock()


def orgid(code):
    with _CACHE_LOCK:
        if code in _CACHE:
            return _CACHE[code]
    try:
        j = post(TOP, {"keyWord": code, "maxNum": 10})
        val = None
        for it in (j if isinstance(j, list) else []):
            if str(it.get("code")) == code:
                val = it.get("orgId")
                break
        if val is None and isinstance(j, list) and j:
            val = j[0].get("orgId")
    except Exception:
        val = None
    with _CACHE_LOCK:
        _CACHE[code] = val
    return val


def pdf_text(url, max_pages=4):
    req = urllib.request.Request("http://static.cninfo.com.cn/" + url,
                                 headers=UA)
    with urllib.request.urlopen(req, timeout=90) as resp:
        blob = resp.read()
    rd = PdfReader(io.BytesIO(blob))
    return "\n".join((pg.extract_text() or "") for pg in rd.pages[:max_pages])


ann = (pd.read_csv(os.path.join(SB, "abolition_announcements.csv"))
       .dropna(subset=["adjunctUrl"]))
first = (ann.sort_values("date").groupby("secCode").first()
         .reset_index()[["secCode", "date"]])
first["code"] = first["secCode"].astype(str).str.zfill(6)
first["ann"] = first["date"].astype(str).str.slice(0, 10)
todo = first[["code", "ann"]].drop_duplicates("code").reset_index(drop=True)

done = {}
if os.path.exists(PROG):
    prev = pd.read_csv(PROG, dtype=str)
    if len(prev):
        prev["code"] = prev["code"].str.zfill(6)
        done = {r.code: r for r in prev.itertuples()}
        print("resuming: %d already done" % len(done), flush=True)

def one(code, d0):
    """Resolve one firm: orgId -> 决议 announcement -> meeting date."""
    rec = {"code": code, "ann": d0, "meet": "", "n_res": 0, "status": ""}
    oid = orgid(code)
    if not oid:
        rec["status"] = "no_orgid"
        return rec
    end = (pd.Timestamp(d0) + pd.Timedelta(days=180)).strftime("%Y-%m-%d")
    try:
        j = post(API, {"pageNum": 1, "pageSize": 30, "column": "szse",
                       "tabName": "fulltext", "plate": "",
                       "stock": "%s,%s" % (code, oid),
                       "searchkey": "股东大会", "secid": "", "category": "",
                       "trade": "", "seDate": "%s~%s" % (d0, end),
                       "sortName": "", "sortType": "", "isHLtitle": "true"})
        anns = j.get("announcements") or []
    except Exception:
        rec["status"] = "query_fail"
        return rec
    keep = [a for a in anns
            if "决议" in re.sub(r"<[^>]+>", "", a.get("announcementTitle") or "")]
    rec["n_res"] = len(keep)
    for a in keep:
        try:
            txt = pdf_text(str(a["adjunctUrl"]))
        except Exception:
            continue
        ds = []
        for m in re.finditer("股东大会|股东会|审议通过", txt):
            seg = txt[max(0, m.start() - 60): m.start() + 120]
            for dm in DATE.finditer(seg):
                ds.append("%04d-%02d-%02d" % tuple(int(x) for x in dm.groups()))
        if ds:
            rec["meet"] = Counter(ds).most_common(1)[0][0]
            break
    rec["status"] = "ok" if rec["meet"] else "no_date"
    return rec


rows = [dict(zip(COLS, [c, done[c].ann, done[c].meet, done[c].n_res,
                        done[c].status]))
        for c in done]
pend = todo[~todo.code.isin(done)]
print("total %d firms; %d to fetch on %d workers"
      % (len(todo), len(pend), WORKERS), flush=True)

t0 = time.time()
n = 0
with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    futs = {ex.submit(one, r.code, r.ann): r.code for r in pend.itertuples()}
    for f in as_completed(futs):
        n += 1
        try:
            rec = f.result()
        except Exception as e:
            rec = {"code": futs[f], "ann": "", "meet": "", "n_res": 0,
                   "status": "worker_error"}
            print("  ERR %s: %s" % (futs[f], e), flush=True)
        rows.append(rec)
        if n % FLUSH == 0 or n == len(pend):
            pd.DataFrame(rows, columns=COLS).to_csv(PROG, index=False,
                                                    encoding="utf-8-sig")
            el = time.time() - t0
            print("  %d/%d  last=%s %s  elapsed %.1fm  eta %.1fm"
                  % (n, len(pend), rec["code"], rec["status"], el / 60,
                     el / n * (len(pend) - n) / 60), flush=True)

df = pd.DataFrame(rows, columns=COLS)
df.to_csv(PROG, index=False, encoding="utf-8-sig")

ok = df[df.meet.astype(str).str.len() == 10].copy()
print("\n=== proposal -> shareholder approval gap ===")
print("resolved %d of %d" % (len(ok), len(df)))
if len(ok):
    ok["gap"] = (pd.to_datetime(ok.meet) - pd.to_datetime(ok.ann)).dt.days
    print(ok.gap.describe(percentiles=[.05, .25, .5, .75, .95]).round(1).to_string())
    print("  negative gaps (approval before notice): %d" % (ok.gap < 0).sum())
    print("  within 1 quarter (<=92d): %.0f%%" % (100 * ok.gap.le(92).mean()))
    print("  same quarter as proposal: %.0f%%" % (100 * (
        pd.to_datetime(ok.meet).dt.to_period("Q")
        == pd.to_datetime(ok.ann).dt.to_period("Q")).mean()))
print()
print(df.status.value_counts().to_string())
