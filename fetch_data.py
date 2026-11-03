import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

def main():
    url = "https://www.gmpplus.org/feed-certification-scheme/scheme-documents/fsa-requirements/"
    
    try:
        r = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(r.content, 'html.parser')
    except Exception as e:
        print(f"Erro: {e}")
        return
    
    docs = []
    for link in soup.find_all('a', href=True):
        text = link.get_text(strip=True)
        if any(x in text for x in ['R1', 'R2', 'R3', 'TS1', 'TS2', 'TS3']):
            docs.append({
                "code": text[:20],
                "title": text[:80],
                "version": "1.0",
                "url": link.get('href', '#')
            })
    
    news = []
    for article in soup.find_all(['article', 'div'], limit=20):
        title = article.find(['h2', 'h3', 'a'])
        if title:
            news.append({
                "title": title.get_text(strip=True)[:100],
                "url": "#",
                "date_published": datetime.now().date().isoformat()
            })
    
    data = {
        "source_page": "https://www.gmpplus.org/feed-certification-scheme/scheme-documents/fsa-requirements/",
        "last_checked": datetime.now().date().isoformat(),
        "documents": docs[:50],
        "news_items": news[:20],
        "change_log": []
    }
    
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Sucesso! {len(docs)} documentos, {len(news)} notícias")

if __name__ == "__main__":
    main()
