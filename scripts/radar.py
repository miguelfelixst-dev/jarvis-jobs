import json, re, html, urllib.request, urllib.parse, xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "jobs.json"

CATEGORIES = {
    "Excel e planilhas": {
        "keywords": ["excel", "spreadsheet", "google sheets", "planilha", "planilhas", "csv",
                     "vba", "power query", "dashboard", "dashboards"],
        "base": 38,
    },
    "Conversão de arquivos": {
        "keywords": ["file conversion", "convert file", "convert files", "pdf to", "word to pdf",
                     "pdf to word", "pdf to excel", "image to text", "document conversion",
                     "conversão", "converter", "pdf", "ocr"],
        "base": 38,
    },
    "Automações simples": {
        "keywords": ["automation", "automate", "workflow automation", "small script",
                     "simple script", "repetitive task", "browser automation", "automação",
                     "automatizar", "macro", "macros", "rpa"],
        "base": 42,
    },
    "Extensões de navegador": {
        "keywords": ["browser extension", "chrome extension", "firefox extension",
                     "opera extension", "userscript", "tampermonkey", "extensão chrome",
                     "extensão de navegador"],
        "base": 50,
    },
    "Extração e organização de dados": {
        "keywords": ["data entry", "data cleaning", "data extraction", "web scraping", "scraping",
                     "data collection", "data formatting", "organize data", "data organization",
                     "copy paste", "copy-paste", "lead list", "research list", "entrada de dados",
                     "extração de dados", "coleta de dados", "organização de dados",
                     "cadastro de dados", "cadastro", "mineração de dados"],
        "base": 40,
    },
    "Produtos digitais": {
        "keywords": ["digital product", "template creation", "notion template", "spreadsheet template",
                     "ebook formatting", "printable", "digital download", "produto digital",
                     "template", "modelo de planilha"],
        "base": 32,
    },
}

BLOCKED_TITLE_TERMS = [
    "senior", "sr.", "lead ", "principal", "manager", "director", "head of",
    "engineer", "software engineer", "data scientist", "scientist", "architect",
    "marketing manager", "sales manager", "recruiter", "product manager", "product owner",
    "customer success", "devops", "full stack", "frontend", "backend", "machine learning",
    "operations partner", "people partner", "talent lead", "chief ", "vp ", "vice president",
]

MARKETPLACE_SOURCES = {"99Freelas", "Workana", "Freelancer", "Upwork", "Reddit r/forhire", "Reddit r/slavelabour", "GitHub"}
PREFERRED_TERMS = [
    "freelance", "freelancer", "contract", "project", "one-time", "one time",
    "short term", "short-term", "part-time", "temporary", "fixed-term", "fixed term",
    "projeto", "freela", "temporário", "contrato",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; JarvisJobs/2.0; +https://github.com/miguelfelixst-dev/jarvis-jobs)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.5",
}

def fetch_text(url, timeout=30):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        charset = r.headers.get_content_charset() or "utf-8"
        return r.read().decode(charset, errors="replace")

def get_json(url):
    req = urllib.request.Request(url, headers={**HEADERS, "Accept":"application/json"})
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

def classify_job(title, desc, tags, source=""):
    title_l = title.lower()
    blob = f"{title} {desc} {' '.join(tags)}".lower()

    if any(term in title_l for term in BLOCKED_TITLE_TERMS):
        return None, 0, []

    marketplace = source in MARKETPLACE_SOURCES
    engagement_hits = [p for p in PREFERRED_TERMS if p in blob]
    if not marketplace and not engagement_hits:
        return None, 0, []

    best_category, best_score, best_hits = None, 0, []

    for category, rule in CATEGORIES.items():
        title_hits = [kw for kw in rule["keywords"] if kw in title_l]
        body_hits = [kw for kw in rule["keywords"] if kw in blob and kw not in title_hits]

        # Em marketplaces de freela aceitamos forte aderência na descrição também;
        # fora deles, o serviço precisa aparecer no título.
        if not title_hits and not (marketplace and len(body_hits) >= 2):
            continue

        score = rule["base"]
        score += min(35, 14 * len(title_hits))
        score += min(18, 5 * len(body_hits))
        score += min(12, 4 * len(engagement_hits))
        if marketplace:
            score += 10
        if "full-time" in blob or "full time" in blob:
            score -= 25

        score = max(0, min(100, score))
        if score > best_score:
            best_category, best_score = category, score
            best_hits = list(dict.fromkeys(title_hits + body_hits + engagement_hits))

    if not best_category or best_score < 50:
        return None, 0, []
    return best_category, best_score, best_hits

def add_job(out, *, source, title, desc, url, date=None, tags=None, meta=None):
    tags = [clean(x) for x in (tags or []) if clean(x)]
    title, desc, url = clean(title), clean(desc), clean(url)
    if not title or not url:
        return
    category, score, hits = classify_job(title, desc, tags, source)
    if not category:
        return
    item = {
        "source": source,
        "title": title[:180],
        "description": desc[:900],
        "url": url,
        "date": normalize_date(date),
        "tags": list(dict.fromkeys(tags + hits))[:14],
        "score": score,
        "category": category,
    }
    if meta:
        item["meta"] = meta
    out.append(item)

def nearest_text(anchor, max_chars=1800):
    node = anchor
    for _ in range(5):
        if node is None:
            break
        txt = clean(node.get_text(" ", strip=True))
        if len(txt) >= 120:
            return txt[:max_chars]
        node = node.parent
    return clean(anchor.parent.get_text(" ", strip=True) if anchor.parent else anchor.get_text(" ", strip=True))[:max_chars]

def scrape_99freelas(out):
    soup = BeautifulSoup(fetch_text("https://www.99freelas.com.br/projects"), "html.parser")
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a.get("href","")
        if "/project/" not in href or href.endswith("/new"):
            continue
        url = urllib.parse.urljoin("https://www.99freelas.com.br", href)
        if url in seen:
            continue
        seen.add(url)
        title = clean(a.get_text(" ", strip=True))
        if len(title) < 4:
            continue
        desc = nearest_text(a)
        add_job(out, source="99Freelas", title=title, desc=desc, url=url, tags=["Brasil", "freelance", "projeto"])

def scrape_workana(out):
    urls = [
        "https://www.workana.com/pt/jobs?country=BR&skills=microsoft-excel",
        "https://www.workana.com/pt/jobs?skills=web-scraping",
        "https://www.workana.com/pt/jobs?skills=data-entry",
        "https://www.workana.com/pt/jobs?skills=python",
    ]
    seen=set()
    for page in urls:
        soup=BeautifulSoup(fetch_text(page), "html.parser")
        for a in soup.find_all("a", href=True):
            href=a.get("href","")
            if "/job/" not in href:
                continue
            url=urllib.parse.urljoin("https://www.workana.com", href)
            if url in seen: continue
            seen.add(url)
            title=clean(a.get_text(" ", strip=True))
            if len(title)<5: continue
            add_job(out, source="Workana", title=title, desc=nearest_text(a), url=url,
                    tags=["freelance","projeto"])

def scrape_freelancer(out):
    pages = [
        "https://www.freelancer.com/jobs/excel/",
        "https://www.freelancer.com/jobs/web-scraping/",
        "https://www.freelancer.com/jobs/data-entry/",
        "https://www.freelancer.com/jobs/automation/",
    ]
    seen=set()
    for page in pages:
        soup=BeautifulSoup(fetch_text(page), "html.parser")
        for a in soup.find_all("a", href=True):
            href=a.get("href","")
            if not ("/projects/" in href or "/jobs/" in href):
                continue
            title=clean(a.get_text(" ", strip=True))
            if len(title)<8 or title.lower() in {"bid now","view job","apply now"}:
                continue
            url=urllib.parse.urljoin("https://www.freelancer.com", href)
            if url in seen or url.rstrip("/") in {p.rstrip("/") for p in pages}: continue
            seen.add(url)
            add_job(out, source="Freelancer", title=title, desc=nearest_text(a), url=url,
                    tags=["freelance","project"])

def scrape_upwork(out):
    pages = [
        "https://www.upwork.com/freelance-jobs/data-scraping/",
        "https://www.upwork.com/freelance-jobs/microsoft-excel/",
        "https://www.upwork.com/freelance-jobs/data-entry/",
        "https://www.upwork.com/freelance-jobs/automation/",
    ]
    seen=set()
    for page in pages:
        soup=BeautifulSoup(fetch_text(page), "html.parser")
        for a in soup.find_all("a", href=True):
            href=a.get("href","")
            if "/freelance-jobs/apply/" not in href:
                continue
            url=urllib.parse.urljoin("https://www.upwork.com", href)
            if url in seen: continue
            seen.add(url)
            title=clean(a.get_text(" ", strip=True))
            if len(title)<5: continue
            add_job(out, source="Upwork", title=title, desc=nearest_text(a), url=url,
                    tags=["freelance","project"])

def scrape_reddit_rss(out, subreddit, source):
    url=f"https://www.reddit.com/r/{subreddit}/new/.rss"
    raw=fetch_text(url)
    root=ET.fromstring(raw)
    ns={"a":"http://www.w3.org/2005/Atom"}
    for entry in root.findall("a:entry", ns):
        title=clean(entry.findtext("a:title", default="", namespaces=ns))
        link_el=entry.find("a:link", ns)
        link=link_el.attrib.get("href","") if link_el is not None else ""
        content=entry.findtext("a:content", default="", namespaces=ns)
        updated=entry.findtext("a:updated", default="", namespaces=ns)
        add_job(out, source=source, title=title, desc=content, url=link, date=updated,
                tags=["forum","freelance","project"])

def github_bounties(out):
    queries = [
        '"excel" is:issue is:open',
        '"web scraping" is:issue is:open',
        '"browser extension" is:issue is:open',
        '"automation" "bounty" is:issue is:open',
    ]
    for q in queries:
        url="https://api.github.com/search/issues?q="+urllib.parse.quote(q)+"&sort=created&order=desc&per_page=20"
        data=get_json(url)
        for j in data.get("items",[]):
            labels=[x.get("name","") for x in j.get("labels",[])]
            body=clean(j.get("body",""))
            # Só entram issues com sinal de recompensa/trabalho contratado.
            blob=(j.get("title","")+" "+body+" "+" ".join(labels)).lower()
            if not any(x in blob for x in ["bounty","paid","payment","reward","$","€","freelance","contract"]):
                continue
            add_job(out, source="GitHub", title=j.get("title",""), desc=body,
                    url=j.get("html_url",""), date=j.get("created_at"), tags=labels+["bounty","project"])

def collect():
    jobs, errors = [], []
    sources = [
        ("99Freelas", scrape_99freelas),
        ("Workana", scrape_workana),
        ("Freelancer", scrape_freelancer),
        ("Upwork", scrape_upwork),
        ("Reddit r/forhire", lambda out: scrape_reddit_rss(out, "forhire", "Reddit r/forhire")),
        ("Reddit r/slavelabour", lambda out: scrape_reddit_rss(out, "slavelabour", "Reddit r/slavelabour")),
        ("GitHub", github_bounties),
    ]
    for name, fn in sources:
        try:
            fn(jobs)
        except Exception as exc:
            errors.append(f"{name}: {type(exc).__name__}: {exc}")

    seen, unique = set(), []
    for job in jobs:
        key = (job.get("url") or job.get("title","").lower()).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(job)

    unique.sort(key=lambda x:(int(x.get("score",0)), str(x.get("date") or "")), reverse=True)
    capped=unique[:300]
    return {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(capped),
        "errors": errors,
        "jobs": capped,
    }

def main():
    payload=collect()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Salvos {len(payload['jobs'])} freelas compatíveis.")
    if payload["errors"]:
        print("Fontes com erro:", " | ".join(payload["errors"]))

if __name__ == "__main__":
    main()
