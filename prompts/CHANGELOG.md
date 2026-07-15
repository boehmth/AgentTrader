# Prompt Changelog

Diese Datei dokumentiert die Iterationen der Agent-Prompts.
Umschalten zwischen Versionen per `.env`:

```
PROMPT_VERSION=v1
```

---

## v1 — Baseline (2026-07-15)

**Inhalt**: Der Zustand nach dem Refactoring auf `prompts/`, `runner/`, `model/`,
`tools/`. Der Agent kennt nur `load`, `buy`, `sell`, `get_prices`, `calculator`.

**Systemprompt**: sehr generisches Ziel („langfristig maximieren"), keine
konkreten Regeln, „nichts tun" ist explizit erlaubt.

**Beobachtetes Verhalten** (15-Tage-Simulation, `gpt-4o-mini`, Startkapital 10 000 €):
- Tag 1: All-in in NVDA (50 Aktien, 99.5 % Kapitaleinsatz).
- Tag 4: Panik-Verkauf mit −2 % Verlust.
- Tage 5–13: **9 Tage nichts.**
- Tag 15: Impulsiver All-in in AMZN am letzten Tag.
- Endstand: 9 798,50 € (**−2.01 %**).

**Problem**:
- Kein Regelwerk → Bauchentscheidungen.
- Keine Diversifikation.
- Nach kleinem Verlust „einfriert" der Agent.
- Aktivität bricht komplett zusammen, dann willkürlicher Last-Minute-Trade.

---

## v2 — Regelbasierter Agent (2026-07-15)

**Zielsetzung**: A + B + C + D + F aus der Diskussion:
- A: Diversifikation (max. 40 % pro Ticker).
- B: Anti-Panik (Halten außer bei klaren Signalen).
- C: Aktivitäts-Zwang (Cash > 30 % → muss investieren).
- D: Datengetriebene Entscheidungen (Rendite explizit berechnen).
- F: Cash-Reserve (min. 10 %).

**Änderungen gegenüber v1**:

1. **Neuer Abschnitt „KENNZAHLEN, DIE DU BERECHNEN SOLLST"**:
   Zwingt zur Berechnung von 20-Tage-Rendite, 5-Tage-Rendite und
   Positions-Anteil vor jeder Entscheidung.

2. **Neuer Abschnitt „HANDELS-REGELN (bindend)"** mit acht Regeln R1–R8:
   - R1: max. 40 % pro Ticker.
   - R2: min. 50 % investiert.
   - R3: min. 10 % Cash-Reserve.
   - R4: keine Round-Trips am selben Tag.
   - R5: Verkauf nur bei Take-Profit >+10 % oder Stop-Loss <−5 %.
   - R6: Kauf nur wenn 5-Tage-Rendite positiv und Ticker-Anteil <30 %.
   - R7: bei Cash >30 % + gültigem Kaufsignal MUSS gekauft werden.
   - R8: keine Käufe bei extremen Anstiegen >20 %, Verkauf bei extremen Rückgängen.

3. **Neuer Abschnitt „TYPISCHER ABLAUF"** vorne, damit die Reihenfolge klar ist.

4. **`tool_descriptions.txt`**:
   - `get_prices` fest auf 20 Tage Historie festgelegt (`operand2="20"`).
   - Explizite Beispiele für `$results[i].prices.0.close` und
     `$results[i].prices.15.close` als Zugriff auf 20-Tage- und
     5-Tage-Vergleichspunkt.
   - „Standard-Berechnungen (Rezepte)" für Rendite und Positions-Anteil
     mit exakter Reihenfolge der Calculator-Aufrufe.
   - Verweis darauf, dass `operand2` bei buy/sell den `latest.close`
     als Referenz nutzen soll.

**Erwartete Wirkung**:
- Weniger All-in-Trades (durch R1).
- Weniger Panik-Verkäufe (durch R5).
- Weniger „9 Tage nichts" (durch R7).
- Nachvollziehbarere Entscheidungen (durch Kennzahlen-Zwang).

**Messung**:
Simulation mit `PROMPT_VERSION=v2` fahren, dann Endstand, Trade-Anzahl,
maximaler Ticker-Anteil und Zahl von Warte-Tagen (nichts getan) mit v1
vergleichen. Zieldaten für v3-Iteration hier eintragen.

---

## v3 — Kompakter, entscheidungs-fokussiert (2026-07-15)

**Motivation aus v2-Lauf**:
- v2 hat den Agenten dazu gebracht, in einer Iteration **50+ Steps** zu
  planen (alle 4 Ticker mit je 5-Tage-Rendite, 20-Tage-Rendite und
  Positionsanteil). Konsequenzen:
    - Jeder Tag brauchte alle 5 Iterationen — trotzdem meist keine
      Entscheidung.
    - Simulation zu langsam (>5 min für Tag 1).
    - Nebenwirkung: `max_tokens=1024` reichte nicht (jetzt 4096, siehe
      Code-Fix).

**Zielsetzung**:
- Der Agent trifft in **max. 2 Iterationen** eine Entscheidung.
- Pro Iteration **max. 6-8 Steps**.
- **Ein Ticker pro Tag** analysieren, nicht alle vier gleichzeitig.

**Änderungen gegenüber v2**:

1. Neuer Abschnitt „KLEINE ITERATIONEN" ganz vorne:
   - „max 6-8 Steps pro Iteration",
   - „max 1 Ticker pro Iteration vollständig analysieren",
   - „Entscheidung ausführen + done=true, auch wenn nicht alle Ticker
     geprüft wurden".

2. Neuer Abschnitt „ARBEITSFLUSS (empfohlen)" mit konkretem 2-Iterations-
   Schema (Iteration 1: load + 1× get_prices, Iteration 2: 3× calculator
   + evtl. buy/sell + done).

3. Regeln komprimiert:
   - Nur EINE Pflicht-Kennzahl: die **5-Tage-Rendite**.
   - 20-Tage-Rendite entfernt (war in v2 selten wirklich gebraucht).
   - Positionsanteil-Berechnung nur noch als optional erwähnt.

4. Regel-Set schlanker:
   - R0 Cash-Reserve (min 10 %).
   - R1 Diversifikation (max 40 % pro Ticker).
   - R2 Verkauf: −5 % oder +7 % 5-Tage-Rendite -> halbe Position raus.
   - R3 Kauf: bei > 30 % Cash und positiver 5-Tage-Rendite -> ~25 % Cash
     in den Ticker mit der höchsten Rendite.
   - R4 Kein Round-Trip.
   - R5 „Nichtstun ist OK, aber max 3 Tage am Stück".

5. R7 (Aktivitätszwang) aus v2 entfernt — führte zu übereiligen Käufen.
   Ersetzt durch weichere Formulierung in R5.

**Erwartete Wirkung**:
- Deutlich schnellere Simulation.
- Tatsächlich getroffene Entscheidungen pro Tag.
- Immer noch diszipliniert (Regeln erhalten).

**Messergebnisse (Sim vom 2026-07-15, 5 Tage, gpt-4o-mini)**:
- Endstand: 10 000,00 €
- Anzahl Trades: **0**
- P&L: 0,00 % (auch Buy&Hold Vergleich: entfällt)
- Wartetage (steps == []): 0 — der Agent hat immer geplant, aber nicht gehandelt.
- Laufzeit pro Tag: ca. 40 s (v2 hätte >5 min gebraucht).

**Beobachtung**:
- v3 ist schnell, aber der Agent trifft nie eine Kaufentscheidung.
- Iteration 1: portfolio.load ✔
- Iteration 2: erneut load + get_prices NVDA ✔
- Iteration 3: nochmals dieselben zwei Schritte (der Agent „vergisst" die
  bisherigen Ergebnisse und plant sie neu).
- Iteration 4: endlich calculator subtract, aber mit **hart kodierten
  Zahlen** statt `$results`-Referenzen.
- Iteration 5: MAX_ITERATIONS aufgebraucht, done nie erreicht.

**Diagnose**:
Der Agent redundiert Steps, weil er den zurückgegebenen `results`-Kontext
nicht als „bereits erledigt" interpretiert. Der Prompt sagt aktuell nicht
explizit: „Wenn ein Schritt in results steht, wiederhole ihn NICHT."

**Idee für v4**:
- Deutliche Ergänzung: „Prüfe zuerst, welche Steps bereits in `results`
  stehen. Wiederhole KEINEN Step, den du dort findest."
- Optional: den Agent zwingen, in der ersten Iteration alle 4 get_prices
  UND die 4 einfachen Renditen zu berechnen, damit er in Iter 2
  entscheiden kann (weniger „ich prüfe erstmal EINEN Ticker"-Wischiwaschi).

---

## Zugehöriger Code-Fix (nicht Teil des Prompt-Versionierung, aber im gleichen Zug):

- `runner/refs.py`: Listen-Index-Support für `$results[i].prices.<n>.close`
  (der v1-Resolver konnte nur Dict-Zugriffe).
- `model/sap.py` + `model/gemini.py`: `max_tokens` bzw. `max_output_tokens`
  konfigurierbar, Default auf 4096 hochgezogen (v2 stieß bei 1024 an
  die Grenze).

---

## v4 — Präskriptiver Arbeitsplan (2026-07-15)

**Motivation aus v3-Lauf**:
- Der Agent hat den `results`-Kontext ignoriert und Steps wiederholt.
- Die 5-Tage-Rendite wurde am Ende zwar berechnet, aber mit hart kodierten
  Zahlen (nicht mit `$results`-Referenzen) — bei mehreren Tickern führte
  das zu Verwechslungen.

**Änderungen gegenüber v3**:
1. Neuer Abschnitt **„DAS WICHTIGSTE — RESULTS IST DEIN GEDÄCHTNIS"**
   ganz oben, mit expliziten „Wiederhole niemals ..."-Beispielen und
   dem Verbot hart kodierter Zahlen.
2. Neuer Abschnitt **„ARBEITSPLAN (2 Iterationen, dann fertig)"** —
   Iteration 1 = 1× load + 4× get_prices, Iteration 2 = 4× calculator
   + 1× buy/sell + done.
3. Regel R3 explizit als „Tag-1 muss kaufen"-Zwang, um „Zögern" zu
   vermeiden.

**Ergebnisse (Sim vom 2026-07-15, 5 Tage)**:

Mit `gpt-4o-mini`:
- Iteration 1 perfekt, aber operand2 des `buy` blieb bei
  `"12@$results[1].latest.close"` — der Resolver löste die Referenz
  nicht auf (Bug: „mixed reference in string").
- Ergebnis: 0 Trades, Endstand 10 000 €.

Mit `anthropic--claude-4.7-opus` (nach Bug-Fixes am Resolver und
`temperature`-Deprecation):
- **5 Trades, +0.54 % P&L in 5 Tagen.**
- Diversifikation über 3 Ticker (NVDA, MSFT, AMZN).
- Cash-Reserve bei ~36 % (R0 eingehalten).
- Jeder Trade wurde mit R0/R1/Anteil-Berechnung im description-Feld
  begründet — genau das didaktische Ziel!

**Beobachtete Schwäche**:
- An 2 aufeinanderfolgenden Tagen NVDA gekauft (Klumpenrisiko).
- R3 empfahl „Ticker mit höchster positiver Rendite" — das war beide
  Male NVDA.

---

## v5 — R3 präzisiert (Ticker-Cooldown, Positionsgröße vom Gesamtwert) (2026-07-15)

**Motivation aus v4-Lauf**:
- Der Agent kaufte am gleichen Ticker zweimal in Folge (NVDA an Tag 1
  und Tag 2). Kein Regel-Bruch, aber Klumpenrisiko.
- „25 % des aktuellen Cash" schrumpft mit jedem Kauf, was zu immer
  kleineren Käufen führt.

**Änderungen gegenüber v4** (nur R3):

1. **Ticker-Cooldown**: „Wenn ein Ticker in den letzten 2 Handelstagen
   schon gekauft wurde, überspringe ihn."
2. **Präferenz für neue Ticker**: „BEVORZUGE Ticker, die du noch nicht
   hältst (holdings[t] == 0)."
3. **Positionsgröße vom GESAMTWERT statt vom Cash**:
   `Ziel = 25 % × (Cash + Equity)`. So bleibt die Zielgröße pro Kauf
   stabil, auch wenn Cash sinkt.
4. **Deckelung durch R0**: Kauf niemals mehr, als Cash − 10 % Total.
5. **Deckelung durch R1**: Zielgröße reduzieren, wenn sonst >40 %
   Ticker-Anteil erreicht würden.
6. **Max. 1 Kauf pro Tag** explizit gemacht.
7. Rest bleibt: Tag-1-Sonderfall, `$results`-Referenz für Preis.

**Erwartete Wirkung**:
- Bei 4 verfügbaren Tickern und Ticker-Cooldown = 2 Tage sollte in
  ~4 Tagen jeder Ticker mindestens einmal drankommen.
- Klumpenrisiko in einer Position wird strukturell ausgeschlossen.

**Messergebnisse (Sim vom 2026-07-15, 5 Tage)**:

### Mit `anthropic--claude-4.7-opus`:
- **Endstand: 10 189,06 € (+1.89 %)**
- 3 Trades: NVDA @Tag1, AMZN @Tag2, MSFT @Tag3.
- **Alle 3 Käufe auf DIFFERENT Ticker** — Cooldown/Präferenz für neue
  Ticker funktioniert perfekt.
- Positionsgrößen aus dem Gesamtwert berechnet (jeweils ~24-25 %).
- Ab Tag 4-5: hält still (keine neuen positiven Signale + Cooldown auf
  NVDA/AMZN/MSFT).

Trade-Log:
```
Tag 1: buy 12 NVDA @202.78  -> total 10000, NVDA=24%
Tag 2: buy 10 AMZN @245.34  -> total 10098, AMZN=24%
Tag 3: buy  6 MSFT @390.99  -> total 10029, MSFT=23%
Tag 4/5: hält
```
Cash blieb bei ~27 %, alle 3 Regeln R0/R1/R3 eingehalten. Sauber.

### Mit `gpt-4.1`:
- **Endstand: 10 023,11 € (+0.23 %)**
- 3 Trades, aber mit interessanten Abweichungen:
  - **MSFT-Kauf mit Bruchteil-Aktie** (5.30 statt 5 oder 6) — R3
    „ganze Aktien" wurde ignoriert.
  - **Verkauf mit Bruchteil** (MSFT von 6.0 auf 5.30) — der Agent hat
    aktiv rebalanciert. Claude tat das nicht.
  - Iteration mit vielen zusätzlichen Berechnungen (auch Positions-
    Werte für Anteil-Prozente).
- Cash-Reserve bei ~56 % (mehr als das Ziel — konservativer).
- Insgesamt „mehr denken, weniger handeln" — typisch gpt-4.1.

### Fazit
- **Claude 4.7 Opus** setzt v5 präziser um: bessere Diversifikation,
  bessere Cash-Auslastung, keine Regel-Verletzung.
- **gpt-4.1** ist etwas kreativer (Bruchteile, aktives Rebalancing),
  hält sich aber weniger streng an die Regel „ganze Aktien".
- Beide sind deutlich besser als v1/gpt-4o-mini (−2.01 %).

**Regel-Verletzungen bei gpt-4.1**:
- Bruchteil-Aktien statt „floor()" auf ganze Zahl.
- **Idee für v6**: „shares MUSS eine ganze Zahl sein — nie Bruchteile.
  Wenn die 25 %-Zielgröße keine ganze Zahl ergibt: floor()."

---

## Vorlage für die nächste Version

```markdown
## v<N> — <Kurztitel> (<YYYY-MM-DD>)

**Zielsetzung**: …

**Änderungen gegenüber v<N-1>**:
1. …

**Erwartete Wirkung**: …

**Messergebnisse (Sim vom <Datum>, N Tage)**:
- Endstand: …
- Anzahl Trades: …
- Max. Ticker-Anteil: …
- Wartetage (steps == []): …