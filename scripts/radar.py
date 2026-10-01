import json, re, html, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "jobs.json"

KEYWORDS = {
    "browser extension": 35, "chrome extension": 35, "firefox extension": 35,
    "automation": 28, "automação": 28, "web scraping": 28, "scraping": 25,
    "data extraction": 25, "extração de dados": 25, "excel": 22,
    "spreadsheet": 22, "google sheets": 22, "csv": 18, "pdf": 18,
    "data entry": 16, "data cleaning": 18, "python": 16, "javascript": 14,
    "file conversion": 18, "convert": 10, "small script": 20, "script": 10,
    "api": 12, "remote": 8, "freelance": 14, "contract": 10,
    "virtual assistant": 12, "research": 10, "data": 8
}
NEGATIVE = {
    "senior": -8, "lead engineer": -12, "principal": -15, "manager": -8,
    "director": -15, "staff engineer": -12
}

def get_json(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "JarvisJobs/1.2 (+https://github.com/miguelfelixst-dev/jarvis-jobs)",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))

def clean(value):
    text = "" if value is None else str(value)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return re.sub(r"\s+", " ", text).strip()

def normalize_date(value):
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()
        except (OverflowError, OSError, ValueError):
            return str(value)
    return str(value)

def score_job(title, desc, tags):
    blob = f"{title} {desc} {' '.join(tags)}".lower()
    score, hits = 0, []
    for key, points in KEYWORDS.items():
        if key in blob:
            score += points
            hits.append(key)
    for key, points in NEGATIVE.items():
        if key in blob:
            score += points
    return max(0, min(100, score)), hits

def add_job(out, *, source, title, desc, url, date=None, tags=None):
    tags = [clean(x) for x in (tags or []) if clean(x)]
    title, desc, url = clean(title), clean(desc), clean(url)
    if not title or not url:
        return
    score, hits = score_job(title, desc, tags)
    if score < 10:
        return
    out.append({
        "source": source,
        "title": title[:180],
        "description": desc[:650],
        "url": url,
        "date": normalize_date(date),
        "tags": list(dict.fromkeys(tags + hits))[:12],
        "score": score,
    })

def remoteok(out):
    data = get_json("https://remoteok.com/api")
    rows = data[1:] if isinstance(data, list) else []
    for j in rows:
        if isinstance(j, dict):
            add_job(out, source="Remote OK", title=j.get("position", ""),
                    desc=j.get("description", ""), url=j.get("url", ""),
                    date=j.get("date") or j.get("epoch"), tags=j.get("tags", []))

def arbeitnow(out):
    data = get_json("https://www.arbeitnow.com/api/job-board-api")
    for j in data.get("data", []):
        add_job(out, source="Arbeitnow", title=j.get("title", ""),
                desc=j.get("description", ""), url=j.get("url", ""),
                date=j.get("created_at"), tags=j.get("tags", []))

def jobicy(out):
    data = get_json("https://jobicy.com/api/v2/remote-jobs?count=50")
    for j in data.get("jobs", []):
        tags = []
        for field in ("jobType", "jobIndustry", "jobGeo"):
            value = j.get(field)
            if isinstance(value, list):
                tags.extend(value)
            elif value:
                tags.append(value)
        add_job(out, source="Jobicy", title=j.get("jobTitle", ""),
                desc=j.get("jobDescription", ""), url=j.get("url", ""),
                date=j.get("pubDate"), tags=tags)

def collect():
    jobs, errors = [], []
    for name, fn in (("Remote OK", remoteok), ("Arbeitnow", arbeitnow), ("Jobicy", jobicy)):
        try:
            fn(jobs)
        except Exception as exc:
            errors.append(f"{name}: {type(exc).__name__}: {exc}")

    seen, unique = set(), []
    for job in jobs:
        key = (job.get("url") or job.get("title", "").lower()).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(job)

    unique.sort(key=lambda x: (int(x.get("score", 0)), str(x.get("date") or "")), reverse=True)
    return {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(unique),
        "errors": errors,
        "jobs": unique[:250],
    }

def main():
    payload = collect()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Salvos {len(payload['jobs'])} trabalhos.")
    if payload["errors"]:
        print("Fontes com erro:", " | ".join(payload["errors"]))

if __name__ == "__main__":
    main()
