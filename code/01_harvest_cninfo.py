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
"""Harvest supervisory-board (监事会) abolition announcements from CNINFO.

Strategy learned from _probe_sb.py: title wording is fragmented, so take the
UNION of several search keys, then filter to the firm's OWN announcements
(third-party bond-trustee reports also match the keyword and must go).

Output: sb_announcements_raw.csv  (one row per announcement, with metadata)
"""
import csv, json, os, re, time, urllib.parse, urllib.request

OUT = DATA
os.makedirs(OUT, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
      "Referer": "http://www.cninfo.com.cn/new/commonUrl?url=disclosure/list/notice"}
API = "http://www.cninfo.com.cn/new/hisAnnouncement/query"

SEARCH_KEYS = ["取消监事会", "不再设监事会", "撤销监事会", "不设监事会",
               "章程修订 监事会", "废止监事会", "取消设置监事会",
               "监事会 审计委员会", "关于修订公司章程"]
WINDOWS = ["2024-01-01~2024-06-30", "2024-07-01~2024-12-31",
           "2025-01-01~2025-06-30", "2025-07-01~2025-12-31",
           "2026-01-01~2026-12-31"]
PAGE = 30


def fetch(searchkey, seDate, page):
    data = {"pageNum": page, "pageSize": PAGE, "column": "szse",
            "tabName": "fulltext", "plate": "", "stock": "", "searchkey": searchkey,
            "secid": "", "category": "", "trade": "", "seDate": seDate,
            "sortName": "", "sortType": "", "isHLtitle": "true"}
    req = urllib.request.Request(API, data=urllib.parse.urlencode(data).encode(),
                                 headers=UA)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:
            if attempt == 3:
                raise
            time.sleep(2 + 2 * attempt)


def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s or "")


rows, seen = [], set()
stats = []
for key in SEARCH_KEYS:
    for win in WINDOWS:
        try:
            j = fetch(key, win, 1)
        except Exception as e:
            stats.append((key, win, "FAILED", str(e)[:40])); continue
        total = j.get("totalRecordNum") or 0
        got = 0
        if total:
            pages = min((total + PAGE - 1) // PAGE, 120)   # safety cap
            for p in range(1, pages + 1):
                jj = j if p == 1 else fetch(key, win, p)
                anns = jj.get("announcements") or []
                if not anns:
                    break
                for a in anns:
                    aid = a.get("announcementId")
                    if aid in seen:
                        continue
                    seen.add(aid)
                    rows.append({
                        "announcementId": aid,
                        "secCode": a.get("secCode"),
                        "secName": a.get("secName"),
                        "title": strip_tags(a.get("announcementTitle")),
                        "date": time.strftime("%Y-%m-%d",
                                              time.localtime((a.get("announcementTime") or 0) / 1000))
                                if a.get("announcementTime") else "",
                        "adjunctUrl": a.get("adjunctUrl"),
                        "matched_key": key,
                        "window": win,
                    })
                    got += 1
                time.sleep(0.25)
        stats.append((key, win, total, got))

print("%-22s %-24s %8s %8s" % ("searchkey", "window", "total", "new"))
print("-" * 70)
for k, w, t, g in stats:
    print("%-22s %-24s %8s %8s" % (k, w, t, g))

print("\nraw rows harvested: %d (deduped by announcementId)" % len(rows))

p = os.path.join(OUT, "sb_announcements_raw.csv")
with open(p, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)
print("saved:", p)
