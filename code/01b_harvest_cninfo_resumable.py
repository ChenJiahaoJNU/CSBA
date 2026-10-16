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

Version 2 -- changes forced by a 600s tool cap that killed v1 with nothing saved:
  * query each search key ONCE over the whole 2024-2026 range (not 5 windows)
  * append to the CSV after EVERY page, so a kill loses at most one page
  * resumable: already-harvested (key, page) are skipped via a state file
"""
import csv, json, os, re, time, urllib.parse, urllib.request

OUT = DATA
os.makedirs(OUT, exist_ok=True)
RAW = os.path.join(OUT, "sb_announcements_raw.csv")
STATE = os.path.join(OUT, "_state.json")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
      "Referer": "http://www.cninfo.com.cn/new/commonUrl?url=disclosure/list/notice"}
API = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
SPAN = "2024-01-01~2026-12-31"
PAGE = 30
KEYS = ["取消监事会", "章程修订 监事会", "不设监事会", "不再设监事会",
        "撤销监事会", "废止监事会", "取消设置监事会", "监事会 审计委员会"]
FIELDS = ["announcementId", "secCode", "secName", "title", "date", "adjunctUrl",
          "matched_key"]


def fetch(key, page):
    data = {"pageNum": page, "pageSize": PAGE, "column": "szse",
            "tabName": "fulltext", "plate": "", "stock": "", "searchkey": key,
            "secid": "", "category": "", "trade": "", "seDate": SPAN,
            "sortName": "", "sortType": "", "isHLtitle": "true"}
    req = urllib.request.Request(API, data=urllib.parse.urlencode(data).encode(),
                                 headers=UA)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 + 2 * attempt)


state = json.load(open(STATE, encoding="utf-8")) if os.path.exists(STATE) else {}
new_file = not os.path.exists(RAW)
fh = open(RAW, "a", newline="", encoding="utf-8-sig")
w = csv.DictWriter(fh, fieldnames=FIELDS)
if new_file:
    w.writeheader()
seen = set(state.get("seen", []))

for key in KEYS:
    j = fetch(key, 1)
    total = j.get("totalRecordNum") or 0
    pages = min((total + PAGE - 1) // PAGE, 100)
    done = state.get(key, 0)
    if done >= pages:
        print("%-22s already done (%d pages)" % (key, done)); continue
    print("%-22s total=%-6d pages=%-4d resuming at %d" % (key, total, pages, done + 1),
          flush=True)
    for p in range(done + 1, pages + 1):
        jj = j if p == 1 else fetch(key, p)
        anns = jj.get("announcements") or []
        if not anns:
            break
        n = 0
        for a in anns:
            aid = a.get("announcementId")
            if aid in seen:
                continue
            seen.add(aid)
            ts = a.get("announcementTime") or 0
            w.writerow({
                "announcementId": aid,
                "secCode": a.get("secCode"),
                "secName": a.get("secName"),
                "title": re.sub(r"<[^>]+>", "", a.get("announcementTitle") or ""),
                "date": time.strftime("%Y-%m-%d", time.localtime(ts / 1000)) if ts else "",
                "adjunctUrl": a.get("adjunctUrl"),
                "matched_key": key,
            })
            n += 1
        fh.flush(); os.fsync(fh.fileno())
        state[key] = p
        state["seen"] = list(seen)
        json.dump(state, open(STATE, "w", encoding="utf-8"))
        print("   p%-4d +%-3d (total seen %d)" % (p, n, len(seen)), flush=True)
        time.sleep(0.2)

fh.close()
print("\nDONE. unique announcements: %d" % len(seen))
print("saved:", RAW)
