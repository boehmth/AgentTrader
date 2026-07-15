# AgentTrader

Ein didaktischer, LLM-basierter Trading-Agent, der einmal pro Tag Kurse
analysiert und über den Kauf/Verkauf von Aktien entscheidet.

**Ziel dieses Projekts**: Zeigen, wie **dynamisches Tool-Calling** funktioniert
— und wie sich die Qualität eines Agents allein durch Textänderungen
(**Prompt Engineering**) verbessern lässt, ohne den Code anzufassen.

---

## Architektur

```
AgentTrader/
├── agent.py                # CLI: ein einzelner Agent-Lauf
├── simulate.py             # CLI + Library: N-Tage-Simulation
├── benchmark.py            # Fährt mehrere Modelle gegeneinander
├── report.py               # Baut aus data/leaderboard.csv eine HTML-Seite
├── plot.py                 # Equity-Kurve + Trade-Marker
│
├── prompts/                # ← reine Texte (Prompt-Versionen)
│   ├── v1/  v2/  ...  v6/
│   ├── CHANGELOG.md
│
├── runner/                 # Orchestrator (Iterations-Loop, $results-Resolver)
├── model/                  # LLM-Provider (Gemini, SAP GenAI Hub)
├── tools/                  # get_prices, calculator, portfolio
├── clock.py                # simuliertes "heute"
├── price_cache.py          # yfinance-Vorab-Cache
│
└── .github/workflows/      # GitHub Actions: täglicher Benchmark
```

Die drei Ebenen des Agents sind **sauber getrennt**:
- **Texte** (`prompts/`) → beschreiben *was* der Agent tun soll.
- **Runner** (`runner/`) → führt die vom Modell gelieferten Steps aus.
- **Model** (`model/`) → tauschbar (Gemini / SAP GenAI Hub / …).
- **Tools** (`tools/`) → was der Agent in der Welt tun kann.

---

## Setup

### 1. Abhängigkeiten
```bash
pip install -r requirements.txt
```

### 2. `.env` anlegen
Kopiere `.env.example` und fülle die Werte aus. Wichtigste Variablen:

```
LLM_PROVIDER=sap              # oder "gemini"
PROMPT_VERSION=v6
TICKERS=NVDA,MSFT,JPM,KO,JNJ,XOM,WMT,DIS

# Für SAP GenAI Hub:
SAP_GENAI_SERVICE_KEY_FILE=./.sap_service_key.json
SAP_GENAI_MODEL=anthropic--claude-4.7-opus
SAP_GENAI_RESOURCE_GROUP=default

# Für Gemini (Fallback):
GOOGLE_API_KEY=...
```

### 3. Service-Key hinterlegen
Für den SAP GenAI Hub die JSON-Datei mit dem Service-Key als
`.sap_service_key.json` im Projekt-Root ablegen. Sie ist in `.gitignore`.

---

## Ein einzelner Agent-Lauf

```bash
python agent.py
python agent.py --model gpt-4o --prompt-version v6
python agent.py --as-of 2025-11-14
```

## Eine 5-Tage-Simulation

```bash
python simulate.py --days 5
python simulate.py --days 15 --model anthropic--claude-4.7-opus --prompt-version v6
```

Output in `data/`:
- `portfolio.csv` — Cash- und Holdings-Verlauf.
- `trades.csv` — Trade-Log (Kauf/Verkauf mit Preis).
- `simulation_equity.csv` — täglicher Kontostand.
- `simulation.png` — Equity-Kurve mit Buy/Sell-Markern.
- `summary.json` — kompakte Zusammenfassung (P&L, Trades, Audit).

## Modelle vergleichen (Benchmark)

```bash
python benchmark.py --days 5
# oder mit expliziter Modellliste:
python benchmark.py --days 5 \
    --models gpt-4o-mini,gpt-4o,anthropic--claude-4.7-opus \
    --prompt-version v6
```

Output pro Lauf:
```
data/runs/<YYYY-MM-DD>/<model>/
    portfolio.csv
    trades.csv
    simulation_equity.csv
    simulation.png
    summary.json
```

Zusätzlich wird `data/leaderboard.csv` ergänzt — eine Zeile pro Modell pro
Datum, ideal für den Zeitreihen-Vergleich.

## HTML-Report

```bash
python report.py
```

Baut aus `data/leaderboard.csv` eine `docs/index.html`. Zeigt:
- Letzten Lauf (Rangliste heute)
- Aggregat (Ø P&L, Best/Worst, Trades pro Modell)
- Zeitreihe des P&L pro Modell

## Täglicher GitHub-Benchmark

Der Workflow `.github/workflows/daily-benchmark.yml` läuft werktags um 20:00 UTC
und tut:

1. Schreibt aus dem GitHub-Secret `SAP_GENAI_SERVICE_KEY_JSON` die Datei
   `.sap_service_key.json`.
2. Führt `python benchmark.py --days 5` aus.
3. Baut den HTML-Report.
4. Löscht die Service-Key-Datei.
5. Commited `data/` und `docs/` zurück ins Repo.
6. Deployed `docs/` auf GitHub Pages.

**Benötigte Secrets** (Settings → Secrets and variables → Actions):
- `SAP_GENAI_SERVICE_KEY_JSON` — der komplette JSON-Inhalt des Service-Keys.

**Manuell auslösen**: `Actions → Daily Benchmark → Run workflow`.

---

## Prompt-Versionen

Der Agent liest aus `prompts/<PROMPT_VERSION>/`. Wechseln über `.env` oder
CLI-Argument `--prompt-version`.

Die Iteration ist in `prompts/CHANGELOG.md` dokumentiert. Kurzer Überblick:

| Version | Fokus | Ergebnis (v4.7 Opus, 5 Tage) |
|---------|-------|--------------|
| v1 | Baseline, generisches Ziel | −2.01 % (15 Tage) |
| v2 | Feste Regeln R1–R8 (zu viele Steps) | zu langsam |
| v3 | Kompakter Arbeitsplan | 0 Trades |
| v4 | „results ist dein Gedächtnis" | +0.54 % |
| v5 | R3 präzisiert (Cooldown, Ziel-% vom Total) | +1.89 % |
| v6 | 8 Ticker aus 5 Sektoren, ganze Aktien | +0.58 % |

---

## Sicherheit

- Service-Keys **niemals** ins Repo commiten. Der Workflow zieht sie zur
  Laufzeit aus GitHub Secrets.
- `.gitignore` blockiert alle üblichen Secret-Dateien.
- **Privates Repo** wird empfohlen für Produktions-Setup.

---

## Lizenz

Didaktisches Projekt, freie Verwendung.