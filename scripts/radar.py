import json, re, html, urllib.request, urllib.parse
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
    "api": 12, "remote": 8, "freelance": 14, "contract": 10
}

NEGATIVE = {
    "senior": -8, "lead engineer": -12, "principal": -15, "manager": -8,
    "director": -15, "staff engineer": -12
}

def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0 JarvisJobs/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))

def clean(s):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    return re.sub(r"\s+", " ", s).strip()

def score_job(title, desc, tags):
    blob = f"{title} {desc} {' '.join(tags)}".lower()
    score = 0
    hits = []
    for k, pts in KEYWORDS.items():
        if k in blob:
            score += pts
            hits.append(k)
    for k, pts in NEGATIVE.items():
        if k in blob:
            score += pts
    return max(0, min(100, score)), hits

def add_job(out, *, source, title, desc, url, date=None, tags=None):
    tags = [str(x) for x in (tags or []) if x]
    title, desc = clean(title), clean(desc)
    score, hits = score_job(title, desc, tags)
    if score < 10:
        return
    out.append({
        "source": source,
        "title": title[:180],
        "description": desc[:650],
        "url": url,
        "date": date,
        "tags": list(dict.fromkeys(tags + hits))[:12],
        "score": score
    })

def remoteok(out):
    data = get_json("https://remoteok.com/api")
    for j in data[1:]:
        if not isinstance(j, dict): continue
        add_job(out, source="Remote OK", title=j.get("position",""),
                desc=j.get("description",""), url=j.get("url",""),
                date=j.get("date"), tags=j.get("tags",[]))

def arbeitnow(out):
    data = get_json("https://www.arbeitnow.com/api/job-board-api")
    for j in data.get("data", []):
        add_job(out, source="Arbeitnow", title=j.get("title",""),
                desc=j.get("description",""), url=j.get("url",""),
                date=j.get("created_at"), tags=j.get("tags",[]))

def jobicy(out):
    url = "https://jobicy.com/api/v2/remote-jobs?count=50"
    data = get_json(url)
    for j in data.get("jobs", []):
        tags = []
        if j.get("jobType"): tags += j["jobType"] if isinstance(j["jobType"], list) else [j["jobType"]]
        if j.get("jobIndustry"): tags += j["jobIndustry"] if isinstance(j["jobIndustry"], list) else [j["jobIndustry"]]
        add_job(out, source="Jobicy", title=j.get("jobTitle",""),
                desc=j.get("jobDescription",""), url=j.get("url",""),
                date=j.get("pubDate"), tags=tags)

jobs=[]
errors=[]
for name,fn in [("Remote OK",remoteok),("Arbeitnow",arbeitnow),("Jobicy",jobicy)]:
    try:
        fn(jobs)
    except Exception as e:
        errors.append(f"{name}: {type(e).__name__}: {e}")

# deduplicação simples por URL/título
seen=set(); unique=[]
for j in jobs:
    key=(j.get("url") or j.get("title","").lower()).strip()
    if not key or key in seen: continue
    seen.add(key); unique.append(j)

unique.sort(key=lambda x:(x.get("score",0), x.get("date") or ""), reverse=True)
payload={
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "count": len(unique),
    "errors": errors,
    "jobs": unique[:250]
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Salvos {len(payload['jobs'])} trabalhos. Erros: {errors or 'nenhum'}")
