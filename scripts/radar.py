import json, re, html, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "jobs.json"

# Só entram oportunidades compatíveis com os serviços que o JARVIS Jobs foi criado para executar.
CATEGORIES = {
    "Excel e planilhas": {
        "keywords": ["excel", "spreadsheet", "google sheets", "planilha", "csv"],
        "base": 35,
    },
    "Conversão de arquivos": {
        "keywords": ["file conversion", "convert file", "convert files", "pdf to", "word to pdf",
                     "pdf to word", "pdf to excel", "image to text", "document conversion"],
        "base": 38,
    },
    "Automações simples": {
        "keywords": ["automation", "automate", "workflow automation", "small script",
                     "simple script", "repetitive task", "browser automation"],
        "base": 42,
    },
    "Extensões de navegador": {
        "keywords": ["browser extension", "chrome extension", "firefox extension",
                     "opera extension", "userscript", "tampermonkey"],
        "base": 50,
    },
    "Extração e organização de dados": {
        "keywords": ["data entry", "data cleaning", "data extraction", "web scraping", "scraping",
                     "data collection", "data formatting", "data整理", "organize data",
                     "data organization", "copy paste", "copy-paste", "lead list", "research list"],
        "base": 40,
    },
    "Produtos digitais": {
        "keywords": ["digital product", "template creation", "notion template", "spreadsheet template",
                     "ebook formatting", "printable", "digital download"],
        "base": 32,
    },
}

# Cargos tradicionais/complexos que não são o foco do projeto.
BLOCKED_TITLE_TERMS = [
    "senior", "sr.", "lead ", "principal", "manager", "director", "head of",
    "engineer", "developer", "software engineer", "data scientist", "scientist",
    "architect", "analyst", "consultant", "accountant", "security",
    "marketing", "sales", "recruiter", "product manager", "product owner",
    "customer success", "devops", "full stack", "frontend", "backend",
    "machine learning", "operations partner", "people partner", "talent lead",
    "generalist", "chief ", "vp ", "vice president",
]

PREFERRED_TERMS = [
    "freelance", "freelancer", "contract", "project", "one-time", "one time",
    "short term", "short-term", "part-time", "temporary", "remote",
]

def get_json(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "JarvisJobs/1.3 (+https://github.com/miguelfelixst-dev/jarvis-jobs)",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))

def clean(value):
    text = "" if value is None else str(value)
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
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

def classify_job(title, desc, tags):
    title_l = title.lower()
    blob = f"{title} {desc} {' '.join(tags)}".lower()

    if any(term in title_l for term in BLOCKED_TITLE_TERMS):
        return None, 0, []

    best_category = None
    best_score = 0
    best_hits = []

    for category, rule in CATEGORIES.items():
        # Regra principal: o serviço precisa estar explícito no TÍTULO.
        # A descrição apenas ajuda a pontuar; ela não pode transformar um emprego
        # genérico em oportunidade para o JARVIS.
        title_hits = [kw for kw in rule["keywords"] if kw in title_l]
        if not title_hits:
            continue

        desc_hits = [kw for kw in rule["keywords"] if kw in blob and kw not in title_hits]
        pref_hits = [p for p in PREFERRED_TERMS if p in blob]

        score = rule["base"]
        score += min(35, 14 * len(title_hits))
        score += min(12, 4 * len(desc_hits))
        score += min(15, 5 * len(pref_hits))

        # Vagas declaradamente full-time perdem prioridade e só passam se
        # o título for extremamente aderente ao serviço.
        if "full-time" in blob or "full time" in blob:
            score -= 15

        score = max(0, min(100, score))
        if score > best_score:
            best_category = category
            best_score = score
            best_hits = list(dict.fromkeys(title_hits + desc_hits + pref_hits))

    if not best_category or best_score < 50:
        return None, 0, []

    return best_category, best_score, best_hits

def add_job(out, *, source, title, desc, url, date=None, tags=None):
    tags = [clean(x) for x in (tags or []) if clean(x)]
    title, desc, url = clean(title), clean(desc), clean(url)
    if not title or not url:
        return

    category, score, hits = classify_job(title, desc, tags)
    if not category:
        return

    out.append({
        "source": source,
        "title": title[:180],
        "description": desc[:650],
        "url": url,
        "date": normalize_date(date),
        "tags": list(dict.fromkeys(tags + hits))[:12],
        "score": score,
        "category": category,
    })

def remoteok(out):
    data = get_json("https://remoteok.com/api")
    rows = data[1:] if isinstance(data, list) else []
    for j in rows:
        if isinstance(j, dict):
            add_job(
                out, source="Remote OK", title=j.get("position", ""),
                desc=j.get("description", ""), url=j.get("url", ""),
                date=j.get("date") or j.get("epoch"), tags=j.get("tags", [])
            )

def arbeitnow(out):
    data = get_json("https://www.arbeitnow.com/api/job-board-api")
    for j in data.get("data", []):
        add_job(
            out, source="Arbeitnow", title=j.get("title", ""),
            desc=j.get("description", ""), url=j.get("url", ""),
            date=j.get("created_at"), tags=j.get("tags", [])
        )

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
        add_job(
            out, source="Jobicy", title=j.get("jobTitle", ""),
            desc=j.get("jobDescription", ""), url=j.get("url", ""),
            date=j.get("pubDate"), tags=tags
        )

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
    capped = unique[:250]
    return {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(capped),
        "errors": errors,
        "jobs": capped,
    }

def main():
    payload = collect()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Salvos {len(payload['jobs'])} trabalhos compatíveis com o JARVIS Jobs.")
    if payload["errors"]:
        print("Fontes com erro:", " | ".join(payload["errors"]))

if __name__ == "__main__":
    main()
