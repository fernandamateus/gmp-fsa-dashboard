# GMP+ FSA – Painel de Monitoramento

Painel estático que acompanha os documentos **R** e **TS** do
[GMP+ FSA Requirements](https://www.gmpplus.org/feed-certification-scheme/scheme-documents/fsa-requirements/)
e as [notícias GMP+](https://www.gmpplus.org/publications/news/) dos últimos 3 meses,
com destaque para os documentos de transporte (TS1.9 e TS3.3).

## Estrutura

| Arquivo | Função |
|---|---|
| `index.html` | Painel (lê `data.json`) |
| `data.json` | Baseline: documentos, versões, histórico de alterações e notícias |
| `fetch_gmp_data.py` | Raspa o site GMP+, compara versões e atualiza `data.json` |
| `.github/workflows/update.yml` | Roda o script todo dia 1 do mês e faz commit do `data.json` |

## Publicar (GitHub Pages)

1. *Settings → Pages → Build and deployment*: Source **Deploy from a branch**, branch `main`, pasta `/ (root)`.
2. O painel fica em `https://<usuario>.github.io/gmp-fsa-dashboard/`.

## Atualização automática

- *Settings → Actions → General → Workflow permissions*: marque **Read and write permissions**.
- Para rodar na hora: aba **Actions → Atualizar dados GMP+ FSA → Run workflow**.
- Se a raspagem falhar ou vier vazia, o `data.json` não é sobrescrito e o job aparece com erro.

## Rodar localmente

```bash
pip install requests beautifulsoup4
python fetch_gmp_data.py
python -m http.server 8000   # abra http://localhost:8000
```

> Abrir o `index.html` direto do disco (`file://`) bloqueia a leitura do `data.json`; use um servidor local ou o GitHub Pages.
