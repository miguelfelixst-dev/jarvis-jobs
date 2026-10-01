import json, re, html, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "jobs.json"

MAX_COMPETITION = 25
PREFERRED_COMPETITION = 10

CATEGORIES = {
    "Excel e planilhas": {
        "keywords": ["excel", "spreadsheet", "google sheets", "planilha", "planilhas", "csv",
                     "vba", "power query", "dashboard", "dashboards"],
        "base": 38,
    },
    "Conversão de arquivos": {
        "keywords": ["conversão", "converter", "pdf", "ocr", "word para pdf", "pdf para word",
                     "pdf para excel", "imagem para texto", "arquivo", "arquivos"],
        "base": 36,
    },
    "Automações simples": {
        "keywords": ["automação", "automatizar", "automation", "macro", "macros", "rpa",
                     "script simples", "tarefa repetitiva", "power automate"],
        "base": 42,
    },
    "Extensões de navegador": {
        "keywords": ["extensão chrome", "extensão de navegador", "chrome extension",
                     "browser extension", "userscript", "tampermonkey", "opera extension"],
        "base": 50,
    },
    "Extração e organização de dados": {
        "keywords": ["entrada de dados", "data entry", "extração de dados", "web scraping", "scraping",
                     "coleta de dados", "organização de dados", "organizar dados", "cadastro de dados",
                     "cadastro", "digitação", "pesquisa online", "mineração de dados"],
        "base": 40,
    },
    "Produtos digitais": {
        "keywords": ["produto digital", "template", "modelo de planilha", "ebook", "e-book",
                     "material digital", "arquivo digital"],
        "base": 32,
    },
}

BLOCKED_TITLE_TERMS = [
    "senior", "sr.", "lead ", "principal", "gerente", "manager", "diretor", "director",
    "engenheiro", "engineer", "cientista", "scientist", "arquiteto", "architect",
    "recrutador", "recruiter", "product manager", "product owner", "devops",
    "full stack", "frontend", "backend", "machine learning", "vaga clt", "clt",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; JarvisJobs/3.0; +https://github.com/miguelfelixst-dev/jarvis-jobs)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def fetch_text(url, timeout=30):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        charset = r.headers.get_content_charset() or "utf-8"
        return r.read().decode(charset, errors="replace")

def clean(value):
    text = "" if value is None else str(value)
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def parse_int(text, patterns):
    for pattern in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            try:
                return int(re.sub(r"\D", "", m.group(1)))
            except Exception:
                pass
    return None

def classify_job(title, desc, source):
    title_l = title.lower()
    blob = f"{title} {desc}".lower()

    if any(term in title_l for term in BLOCKED_TITLE_TERMS):
        return None, 0, []

    best_category, best_score, best_hits = None, 0, []
    for category, rule in CATEGORIES.items():
        title_hits = [kw for kw in rule["keywords"] if kw in title_l]
        body_hits = [kw for kw in rule["keywords"] if kw in blob and kw not in title_hits]
        if not title_hits and len(body_hits) < 2:
            continue

        score = rule["base"]
        score += min(35, 14 * len(title_hits))
        score += min(20, 5 * len(body_hits))

        if source in {"99Freelas", "Workana", "Freelancer.com.br", "GetNinjas"}:
            score += 10

        score = min(100, score)
        if score > best_score:
            best_category = category
            best_score = score
            best_hits = list(dict.fromkeys(title_hits + body_hits))

    if not best_category or best_score < 50:
        return None, 0, []
    return best_category, best_score, best_hits

def competition_bonus(value):
    if value is None:
        return 0
    if value <= 3:
        return 20
    if value <= 7:
        return 15
    if value <= 10:
        return 10
    if value <= 15:
        return 5
    return 0

def add_job(out, *, source, title, desc, url, date=None, competition=None,
            competition_label="propostas", budget=None, status=None):
    title, desc, url = clean(title), clean(desc), clean(url)
    if not title or not url:
        return
    if status and clean(status).lower() not in {"aberto", "aberta", "seleção", "selecao", "ativo", "ativa"}:
        return
    if competition is not None and competition > MAX_COMPETITION:
        return

    category, score, hits = classify_job(title, desc, source)
    if not category:
        return
    score = min(100, score + competition_bonus(competition))

    out.append({
        "source": source,
        "title": title[:180],
        "description": desc[:900],
        "url": url,
        "date": date,
        "tags": hits[:12],
        "score": score,
        "category": category,
        "meta": {
            "competition": competition,
            "competition_label": competition_label,
            "budget": clean(budget) if budget else None,
            "status": clean(status) if status else None,
        },
    })

def scrape_99freelas(out):
    soup = BeautifulSoup(fetch_text("https://www.99freelas.com.br/projects"), "html.parser")
    candidates=[]
    seen=set()
    for a in soup.find_all("a", href=True):
        href=a.get("href","")
        if "/project/" not in href:
            continue
        url=urllib.parse.urljoin("https://www.99freelas.com.br", href)
        if url in seen: continue
        seen.add(url)
        title=clean(a.get_text(" ", strip=True))
        if len(title) < 5: continue
        if not classify_job(title, "", "99Freelas")[0]:
            continue
        candidates.append((title,url))
        if len(candidates) >= 18:
            break

    for title,url in candidates:
        try:
            detail=BeautifulSoup(fetch_text(url), "html.parser")
            text=clean(detail.get_text(" ", strip=True))
            if "Fechado" in text or "Cancelado" in text:
                continue
            proposals=parse_int(text,[r"Propostas:\s*(\d+)", r"Propostas\s*\((\d+)\)"])
            if proposals is not None and proposals > MAX_COMPETITION:
                continue
            desc=""
            h=detail.find(lambda tag: tag.name in ["h1","h2"] and "Descrição do Projeto" in clean(tag.get_text()))
            if h:
                parts=[]
                for sib in h.find_all_next():
                    if sib.name in ["h1","h2"] and sib is not h:
                        break
                    t=clean(sib.get_text(" ", strip=True))
                    if t and t not in parts:
                        parts.append(t)
                    if sum(map(len,parts))>1200: break
                desc=" ".join(parts)
            if not desc:
                desc=text[:1200]
            budget_match=re.search(r"(Valor Mínimo:\s*R\$\s*[\d\.,]+|Orçamento:\s*[^|]+)", text, re.I)
            budget=budget_match.group(1) if budget_match else None
            date_match=re.search(r"(\d{2}/\d{2}/\d{4})\s+às", text)
            date=date_match.group(1) if date_match else None
            add_job(out, source="99Freelas", title=title, desc=desc, url=url, date=date,
                    competition=proposals, competition_label="propostas", budget=budget, status="Aberto")
        except Exception:
            continue

def scrape_workana(out):
    pages=[
        "https://www.workana.com/pt/jobs?country=BR&skills=microsoft-excel",
        "https://www.workana.com/pt/jobs?country=BR&skills=data-entry",
        "https://www.workana.com/pt/jobs?country=BR&skills=web-scraping",
        "https://www.workana.com/pt/jobs?country=BR&skills=python",
    ]
    seen=set()
    candidates=[]
    for page in pages:
        try:
            soup=BeautifulSoup(fetch_text(page), "html.parser")
        except Exception:
            continue
        for a in soup.find_all("a", href=True):
            href=a.get("href","")
            if "/job/" not in href:
                continue
            url=urllib.parse.urljoin("https://www.workana.com", href)
            if url in seen: continue
            seen.add(url)
            title=clean(a.get_text(" ", strip=True))
            if len(title)<5: continue
            if not classify_job(title, "", "Workana")[0]:
                continue
            candidates.append((title,url))
            if len(candidates)>=20: break
        if len(candidates)>=20: break

    for title,url in candidates:
        try:
            detail=BeautifulSoup(fetch_text(url), "html.parser")
            text=clean(detail.get_text(" ", strip=True))
            if "Projeto fechado" in text or "Fechado" in text:
                continue
            proposals=parse_int(text,[r"(\d+)\s+Propostas"])
            interested=parse_int(text,[r"(\d+)\s+Freelancers interessados"])
            comp=proposals if proposals is not None else interested
            if comp is not None and comp > MAX_COMPETITION:
                continue
            desc=""
            h=detail.find("h1")
            if h:
                node=h.parent
                desc=clean(node.get_text(" ", strip=True))[:1500] if node else text[:1500]
            add_job(out, source="Workana", title=title, desc=desc or text[:1500], url=url,
                    competition=comp, competition_label="propostas", status="Aberto")
        except Exception:
            continue

def scrape_freelancer_br(out):
    pages=[
        "https://freelancer.com.br/projetos/s/excel",
        "https://freelancer.com.br/projetos/s/microsoft-excel",
        "https://freelancer.com.br/projetos/s/automa%C3%A7%C3%A3o",
        "https://freelancer.com.br/projetos/s/automa%C3%A7%C3%A3o-de-processos",
    ]
    seen=set()
    for page in pages:
        try:
            soup=BeautifulSoup(fetch_text(page), "html.parser")
        except Exception:
            continue
        text=clean(soup.get_text("\n", strip=True))
        # captura blocos textuais iniciando por "Ativo"
        blocks=re.split(r"(?=Ativo\s)", text)
        for block in blocks:
            if "Status Aberto" not in block and "Status Seleção" not in block and "Status Selecao" not in block:
                continue
            interested=parse_int(block,[r"(\d+)\s+interessados"])
            if interested is not None and interested > MAX_COMPETITION:
                continue
            # tenta casar o título do projeto com um link da página
            title_match=re.search(r"Projeto\s+(.+?)\s+Categoria", block)
            if not title_match:
                continue
            title=clean(title_match.group(1))
            if not classify_job(title, block, "Freelancer.com.br")[0]:
                continue
            candidate=None
            for a in soup.find_all("a", href=True):
                if clean(a.get_text(" ",strip=True))==title:
                    candidate=urllib.parse.urljoin("https://freelancer.com.br",a["href"])
                    break
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            budget_match=re.search(r"Orçamento\s+(.+?)\s+Localização", block)
            budget=budget_match.group(1) if budget_match else None
            add_job(out, source="Freelancer.com.br", title=title, desc=block[:1400], url=candidate,
                    competition=interested, competition_label="interessados", budget=budget, status="Aberto")

def scrape_getninjas(out):
    pages=[
        "https://www.getninjas.com.br/consultoria/auxilio-administrativo/planilhas-e-relatorios",
        "https://www.getninjas.com.br/aulas/tarefas/excel",
        "https://www.getninjas.com.br/design-e-tecnologia/desenvolvimento-de-sites-e-sistemas",
    ]
    seen=set()
    for page in pages:
        try:
            soup=BeautifulSoup(fetch_text(page), "html.parser")
        except Exception:
            continue
        for a in soup.find_all("a", href=True):
            href=a.get("href","")
            if "/orcamentos/" not in href:
                continue
            url=urllib.parse.urljoin("https://www.getninjas.com.br", href)
            if url in seen: continue
            seen.add(url)
            try:
                detail=BeautifulSoup(fetch_text(url), "html.parser")
                text=clean(detail.get_text(" ", strip=True))
                if "Pedido atendido" in text:
                    continue
                h1=detail.find("h1")
                title=clean(h1.get_text(" ",strip=True)) if h1 else clean(a.get_text(" ",strip=True))
                if not title or len(title)<10:
                    continue
                add_job(out, source="GetNinjas", title=title, desc=text[:1500], url=url,
                        competition=None, competition_label="orçamentos", status="Aberto")
            except Exception:
                continue

def collect():
    jobs, errors=[],[]
    sources=[
        ("99Freelas", scrape_99freelas),
        ("Workana", scrape_workana),
        ("Freelancer.com.br", scrape_freelancer_br),
        ("GetNinjas", scrape_getninjas),
    ]
    for name,fn in sources:
        try:
            fn(jobs)
        except Exception as exc:
            errors.append(f"{name}: {type(exc).__name__}: {exc}")

    seen=set(); unique=[]
    for job in jobs:
        key=job["url"].strip()
        if not key or key in seen:
            continue
        seen.add(key); unique.append(job)

    unique.sort(key=lambda x:(
        -(x.get("meta",{}).get("competition") if x.get("meta",{}).get("competition") is not None else 999),
        int(x.get("score",0))
    ), reverse=True)

    # Reordena explicitamente: menor concorrência primeiro, depois maior score.
    unique.sort(key=lambda x:(
        x.get("meta",{}).get("competition") if x.get("meta",{}).get("competition") is not None else 999,
        -int(x.get("score",0))
    ))

    capped=unique[:120]
    return {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(capped),
        "errors": errors,
        "rules": {
            "languages": ["pt-BR","pt-PT"],
            "max_competition": MAX_COMPETITION,
            "preferred_competition": PREFERRED_COMPETITION,
            "sources": ["99Freelas","Workana","Freelancer.com.br","GetNinjas"],
        },
        "jobs": capped,
    }

def main():
    payload=collect()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Salvos {len(payload['jobs'])} projetos em português com até {MAX_COMPETITION} concorrentes.")
    if payload["errors"]:
        print("Fontes com erro:", " | ".join(payload["errors"]))

if __name__ == "__main__":
    main()
