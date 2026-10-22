#!/usr/bin/env python3
"""Extract tentative 28卒 application deadlines from public official pages only.
All machine-extracted dates are labelled unverified. Respect robots.txt.
"""
from __future__ import annotations
import hashlib
import json
import pathlib
import re
import sys
import time
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

ROOT = pathlib.Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))
USER_AGENT = "ShukatsuTracker/1.0 (personal deadline checker; robots respected)"
MARKER = re.compile(r"(?:応募締切|提出締切|申込締切|エントリー締切|締め切り|締切日|応募期限|申込期限|提出期限|エントリー期限|応募期間|受付期間)")
DATE = re.compile(r"(?:(20\d{2})\s*[年./-]\s*)?(1[0-2]|0?[1-9])\s*[月./-]\s*(3[01]|[12]\d|0?[1-9])\s*日?")
TIME = re.compile(r"(?<!\d)([01]?\d|2[0-3])\s*[:：時]\s*([0-5]\d)?\s*分?(?!\d)")
TOKENS_28 = re.compile(r"(?:2028|28卒|28年卒|2028年卒|2028年度)")
OLD = re.compile(r"(?:2027年卒|2027卒|27卒のみ|2026卒|26卒のみ)")

def official_date(year: str | None, month: str, day: str, now: date) -> date | None:
    try:
        m, d = int(month), int(day)
        if year:
            return date(int(year), m, d)
        for y in (now.year, now.year + 1):
            candidate = date(y, m, d)
            if candidate >= now - timedelta(days=21):
                return candidate
    except ValueError:
        pass
    return None

def extract(page: str, company: str, industry: str, url: str, now: date) -> list[dict]:
    soup = BeautifulSoup(page, "html.parser")
    for el in soup(["script", "style", "noscript", "footer", "nav"]):
        el.decompose()
    if not TOKENS_28.search(soup.get_text(" ", strip=True) + " " + url):
        return []
    pieces = []
    for tag in soup.select("h1,h2,h3,h4,p,li,td,dd,dt,div"):
        if tag.name == "div" and tag.find(["h1","h2","h3","p","li","td","dd","dt"]):
            continue
        txt = re.sub(r"\s+", " ", tag.get_text(" ", strip=True))
        if 18 <= len(txt) <= 360 and MARKER.search(txt) and DATE.search(txt):
            pieces.append(txt)
    results, seen = [], set()
    for snippet in pieces:
        if OLD.search(snippet) and not TOKENS_28.search(snippet):
            continue
        if re.search(r"(?:募集終了|受付終了|応募終了|終了しました|受付を終了)", snippet):
            continue
        for found in DATE.finditer(snippet):
            window = snippet[max(0, found.start()-65):min(len(snippet), found.end()+65)]
            if not MARKER.search(window):
                continue
            dt = official_date(*found.groups(), now)
            if dt is None or not (now <= dt <= date(2028, 3, 31)):
                continue
            if OLD.search(window) and not TOKENS_28.search(window):
                continue
            timematch = TIME.search(window)
            clock = f"{int(timematch.group(1)):02d}:{int(timematch.group(2) or 0):02d}" if timematch else ""
            summary = snippet[:150]
            digest = hashlib.sha256((company+"|"+url+"|"+str(dt)+"|"+summary).encode()).hexdigest()[:14]
            key = (company, dt.isoformat(), summary)
            if key in seen:
                continue
            seen.add(key)
            results.append({
                "id":"auto-"+digest,
                "company":company,
                "program":("【自動抽出・要確認】"+summary)[:175],
                "date":dt.isoformat(),
                "time":clock,
                "industry":industry,
                "type":"イベント" if "イベント" in snippet or "セミナー" in snippet else "インターン" if "インターン" in snippet else "本選考",
                "source":"公式サイトのテキストを機械抽出",
                "sourceType":"auto",
                "verification":"unverified",
                "priority":1,
                "status":"未着手",
                "favorite":False,
                "url":url,
                "note":"締切候補は機械抽出された未確認情報です。開催日や別学年を誤認する場合があります。必ず公式募集要項で確認してください。"
            })
    return results

def allowed(session: requests.Session, url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https" or any(x in parsed.path.lower() for x in ("/login", "/mypage", "/signin")):
        return False
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        res = session.get(robots_url, timeout=13)
        if res.status_code == 404:
            return True
        if res.status_code != 200:
            print(f"robots unavailable ({res.status_code}): {robots_url}", file=sys.stderr)
            return False
        rp = RobotFileParser(robots_url)
        rp.parse(res.text.splitlines())
        return rp.can_fetch(USER_AGENT, url)
    except requests.RequestException as exc:
        print(f"robots fetch failed {url}: {exc}", file=sys.stderr)
        return False

def main() -> int:
    cfg = json.loads((ROOT/"data"/"sources.json").read_text(encoding="utf8"))
    path = ROOT/"data"/"deadlines.json"
    now = datetime.now(JST).date()
    found, health = [], []
    with requests.Session() as session:
        session.headers.update({"User-Agent":USER_AGENT,"Accept-Language":"ja-JP,ja;q=0.9"})
        for entry in cfg["sources"]:
            url = entry["url"]
            try:
                if not allowed(session, url):
                    health.append({"company":entry["company"],"status":"blocked_or_robots"})
                    continue
                resp = session.get(url, timeout=18)
                resp.raise_for_status()
                if len(resp.content) > 2_000_000:
                    raise ValueError("page too large")
                candidates = extract(resp.text,entry["company"],entry["industry"],url,now)
                found.extend(candidates)
                health.append({"company":entry["company"],"status":"ok","found":len(candidates)})
            except Exception as exc:
                print(f"fetch failed {url}: {exc}", file=sys.stderr)
                health.append({"company":entry["company"],"status":"failed"})
            time.sleep(1.2)
    try:
        previous = json.loads(path.read_text(encoding="utf8"))
    except (OSError, ValueError):
        previous = {}
    if not any(x["status"]=="ok" for x in health):
        found = previous.get("items",[])
    else:
        successful = {x["company"] for x in health if x["status"]=="ok"}
        found += [x for x in previous.get("items",[]) if x.get("company") not in successful and x.get("date","") >= now.isoformat()]
    merged = {x["id"]:x for x in found}
    data = {
        "schemaVersion":1,
        "generatedAt":datetime.now(JST).isoformat(timespec="seconds"),
        "status":"complete" if all(x["status"]=="ok" for x in health) else "partial",
        "checkedSources":health,
        "items":sorted(merged.values(),key=lambda x:(x["date"],x["company"],x["id"]))
    }
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print(f"Checked {len(health)} official pages, candidate count {len(data['items'])}, status={data['status']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
