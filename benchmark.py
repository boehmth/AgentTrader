# benchmark.py — Fährt eine Simulation für mehrere Modelle nacheinander.
#
# Verwendung:
#   python benchmark.py --days 5 --prompt-version v6
#   python benchmark.py --days 15 --models gpt-4o-mini,gpt-4o,anthropic--claude-4.5-haiku
#
# Struktur der Ergebnisse:
#   data/runs/<YYYY-MM-DD>/<model>/portfolio.csv
#   data/runs/<YYYY-MM-DD>/<model>/trades.csv
#   data/runs/<YYYY-MM-DD>/<model>/simulation_equity.csv
#   data/runs/<YYYY-MM-DD>/<model>/simulation.png
#   data/runs/<YYYY-MM-DD>/<model>/summary.json
#
# Zusätzlich (append):
#   data/leaderboard.csv   — eine Zeile pro Modell pro Datum

import argparse
import json
import os
import re
from datetime import date
from typing import List

from dotenv import load_dotenv
load_dotenv()

import pandas as pd

from simulate import run_simulation


DEFAULT_MODELS = [
    "gpt-4o-mini",
    "gpt-4o",
    "gpt-4.1",
    "anthropic--claude-4.5-haiku",
    "anthropic--claude-4.7-opus",
]


def _sanitize(name: str) -> str:
    """Modellnamen -> filesystem-safe Ordnername."""
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)


def _append_leaderboard(row: dict, path: str = "data/leaderboard.csv") -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    df = pd.DataFrame([row])
    header = not os.path.exists(path)
    df.to_csv(path, mode="a", header=header, index=False)


def run_benchmark(models: List[str],
                  days: int = 5,
                  prompt_version: str = None,
                  run_root: str = "data/runs",
                  ) -> List[dict]:
    """Fährt die Simulation für jedes Modell und aggregiert Ergebnisse."""
    today = date.today().isoformat()
    print(f"[benchmark] Datum:   {today}")
    print(f"[benchmark] Modelle: {models}")
    print(f"[benchmark] Tage:    {days}")
    print(f"[benchmark] Prompt:  {prompt_version or os.getenv('PROMPT_VERSION', 'v1')}")

    all_summaries = []

    for model in models:
        model_dir = os.path.join(run_root, today, _sanitize(model))
        print("\n" + "=" * 60)
        print(f"[benchmark] Starte Simulation für {model}")
        print(f"[benchmark] Output: {model_dir}")
        print("=" * 60)

        try:
            summary = run_simulation(
                days=days,
                model=model,
                prompt_version=prompt_version,
                data_dir=model_dir,
                plot=True,
            )
        except Exception as e:
            summary = {"model": model, "error": str(e)}
            print(f"[benchmark] FEHLER bei {model}: {e}")

        all_summaries.append(summary)

        # Leaderboard-Zeile
        row = {
            "run_date": today,
            "model": summary.get("model", model),
            "prompt_version": summary.get("prompt_version", ""),
            "days": summary.get("days", 0),
            "start_date": summary.get("start_date", ""),
            "end_date": summary.get("end_date", ""),
            "start_total": summary.get("start_total", None),
            "end_total": summary.get("end_total", None),
            "pnl_abs": summary.get("pnl_abs", None),
            "pnl_pct": summary.get("pnl_pct", None),
            "trades": summary.get("trades", 0),
            "audit_ok": summary.get("audit_ok", False),
            "error": summary.get("error", ""),
        }
        _append_leaderboard(row)

    # Bench-Summary
    bench_dir = os.path.join(run_root, today)
    os.makedirs(bench_dir, exist_ok=True)
    with open(os.path.join(bench_dir, "benchmark_summary.json"), "w", encoding="utf-8") as f:
        json.dump(all_summaries, f, ensure_ascii=False, indent=2)

    # Compact Tabelle
    print("\n" + "=" * 60)
    print(" BENCHMARK SUMMARY")
    print("=" * 60)
    rows = []
    for s in all_summaries:
        rows.append({
            "model": s.get("model", "?"),
            "trades": s.get("trades", 0),
            "start": s.get("start_total", 0),
            "end": s.get("end_total", 0),
            "pnl_%": s.get("pnl_pct", 0),
            "audit": s.get("audit_ok", False),
            "error": s.get("error", "")[:60],
        })
    print(pd.DataFrame(rows).to_string(index=False))

    return all_summaries


def _parse():
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=5)
    p.add_argument("--models", type=str, default=",".join(DEFAULT_MODELS),
                   help="Komma-separierte Liste von Modellen")
    p.add_argument("--prompt-version", type=str, default=None)
    p.add_argument("--run-root", type=str, default="data/runs")
    return p.parse_args()


def main():
    args = _parse()
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    run_benchmark(models=models,
                  days=args.days,
                  prompt_version=args.prompt_version,
                  run_root=args.run_root)


if __name__ == "__main__":
    main()