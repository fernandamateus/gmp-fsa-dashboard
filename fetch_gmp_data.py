"""
Atualiza data.json com os documentos R/TS do GMP+ FSA Requirements e as noticias
GMP+ dos ultimos 3 meses.

- Le o data.json atual como baseline (preserva categorias, historicos e logs).
- Compara versoes: cada mudanca vira uma entrada em change_log.
- Noticias que ainda nao estavam em news_log sao registradas como novas.
- Se a raspagem falhar ou vier vazia, o data.json NAO e sobrescrito (exit 1).
"""
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE = "https://www.gmpplus.org"
SOURCE_PAGE = BASE + "/feed-certification-scheme/scheme-documents/fsa-requirements/"
NEWS_PAGE = BASE + "/publications/news/"
DATA_FILE = Path(__file__).with_name("data.json")
NEWS_WINDOW_DAYS = 92  # ~3 meses
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; gmp-fsa-dashboard/1.0)"}

TAB_CATEGORY = {
    "requirements": "Geral (FSMS)",
    "technical specifications": "Geral (FSMS)",
    "country notes": "Nota de pais",
    "hygiene codes": "Codigo de higiene",
    "laboratory": "Laboratorio",
}
TRANSPORT_CODES = {"TS1.9", "TS3.3"}
CODE_RE = re.compile(r"^\s*((?:R|TS)\s?\d+(?:\.\d+)*)\s*(.*)$", re.S)
MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"], start=1)}


def get(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")


def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


def slug_from_url(url):
    return url.rstrip("/").split("/")[-1]


def guess_category(code, title, tab_name):
    if code in TRANSPORT_CODES or "transport" in title.lower():
        return "Transporte (especifico)"
    if code.startswith("TS1.7") and title.lower() != "monitoring":
        return "Monitoramento / listas"
    if code in {"TS1.10", "TS1.11"}:
        return "Producao / operacional"
    if code.startswith("TS3."):
        return "Comercio (trade)"
    return TAB_CATEGORY.get(tab_name.lower(), "Geral (FSMS)")


def scrape_documents(previous_by_id):
    soup = get(SOURCE_PAGE)
    tab_names = {}
    for tab in soup.select("[role=tab]"):
        target = tab.get("aria-controls") or (tab.get("data-bs-target") or "").lstrip("#")
        if target:
            tab_names[target] = clean(tab.get_text())

    docs = []
    for card in soup.select("section.c-card__doc"):
        h3 = card.find(["h3", "h2", "h4"])
        if not h3:
            continue
        m = CODE_RE.match(clean(h3.get_text()))
        if not m:
            continue
        code = m.group(1).replace(" ", "")
        title = m.group(2).strip(" -–")
        title = re.sub(r"^Monitoring\s*[–-]\s*", "Monitoring - ", title)

        ver_el = card.select_one(".c-card__doc-version")
        version = clean(ver_el.get_text()).replace("Version", "").strip() if ver_el else ""

        links = card.find_all("a", href=True)
        view = next((a for a in links if clean(a.get_text()).lower() == "view online"), None)
        view = view or (links[0] if links else None)
        view_url = urljoin(BASE, view["href"]) if view else SOURCE_PAGE

        doc_id = slug_from_url(view_url) if view else f"{code}-{title}".lower()
        pane = card.find_parent(attrs={"role": "tabpanel"})
        tab_name = tab_names.get(pane.get("id"), "") if pane else ""
        prev = previous_by_id.get(doc_id, {})

        docs.append({
            "id": doc_id,
            "code": code,
            "title": title,
            "category": prev.get("category") or guess_category(code, title, tab_name),
            "version": version,
            "view_url": view_url,
        })
    return docs


def parse_news_date(text):
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", text or "")
    if not m or m.group(2).lower() not in MONTHS:
        return None
    return date(int(m.group(3)), MONTHS[m.group(2).lower()], int(m.group(1)))


def scrape_news(today):
    soup = get(NEWS_PAGE)
    limit = today - timedelta(days=NEWS_WINDOW_DAYS)
    items, seen = [], set()
    for a in soup.select("a.publications__item"):
        url = urljoin(BASE, a.get("href", ""))
        title_el = a.select_one(".publications__item-title")
        date_el = a.select_one(".publications__item-date")
        published = parse_news_date(date_el.get_text() if date_el else "")
        if not title_el or not published or url in seen:
            continue
        seen.add(url)
        if published >= limit:
            items.append({"url": url, "title": clean(title_el.get_text()),
                          "date_published": published.isoformat()})
    items.sort(key=lambda n: n["date_published"], reverse=True)
    return items


def main():
    today = date.today()
    data = json.loads(DATA_FILE.read_text(encoding="utf-8")) if DATA_FILE.exists() else {}
    previous_docs = {d.get("id") or d.get("code"): d for d in data.get("documents", [])}

    try:
        docs = scrape_documents(previous_docs)
        news = scrape_news(today)
    except Exception as exc:  # rede, HTML alterado etc.
        print(f"ERRO na raspagem: {exc}", file=sys.stderr)
        sys.exit(1)

    if not docs:
        print("ERRO: nenhum documento encontrado; data.json mantido sem alteracoes.", file=sys.stderr)
        sys.exit(1)

    checked = today.isoformat()
    change_log = data.get("change_log", [])
    for d in docs:
        prev = previous_docs.get(d["id"])
        if prev and prev.get("version") and prev["version"] != d["version"]:
            change_log.append({"id": d["id"], "code": d["code"], "title": d["title"],
                               "old_version": prev["version"], "new_version": d["version"],
                               "detected_at": checked})
            print(f"Atualizado: {d['code']} {d['title']} {prev['version']} -> {d['version']}")
        elif not prev and previous_docs:
            change_log.append({"id": d["id"], "code": d["code"], "title": d["title"],
                               "old_version": "(novo documento)", "new_version": d["version"],
                               "detected_at": checked})
            print(f"Novo documento: {d['code']} {d['title']}")

    news_log = data.get("news_log", [])
    known = {n["url"] for n in news_log}
    for n in news:
        if n["url"] not in known:
            news_log.append({"url": n["url"], "detected_at": checked})

    data.update({
        "source_page": SOURCE_PAGE,
        "news_page": NEWS_PAGE,
        "scope": data.get("scope") or "Todos os documentos R e TS da pagina GMP+ FSA Requirements",
        "last_checked": checked,
        "documents": docs,
        "change_log": change_log,
        "news_items": news,
        "news_log": news_log,
    })
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: {len(docs)} documentos, {len(news)} noticias (ultimos {NEWS_WINDOW_DAYS} dias).")


if __name__ == "__main__":
    main()
