# report.py — Baut aus data/leaderboard.csv eine HTML-Übersicht.
#
# Verwendung:
#   python report.py
#   python report.py --leaderboard data/leaderboard.csv --out docs/index.html

import argparse
import os
from html import escape
from typing import Optional

import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def _plot_pnl_history(leaderboard: pd.DataFrame, out_png: str) -> None:
    """Zeichnet Zeitreihe des P&L pro Modell."""
    if leaderboard.empty:
        return
    fig, ax = plt.subplots(figsize=(11, 5))

    for model, sub in leaderboard.groupby("model"):
        sub = sub.sort_values("run_date")
        ax.plot(sub["run_date"], sub["pnl_pct"], marker="o", label=model)

    ax.axhline(0, color="gray", linewidth=0.5)
    ax.set_title("Daily benchmark: P&L in % pro Modell")
    ax.set_xlabel("Run-Datum")
    ax.set_ylabel("P&L in %")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=8)
    fig.autofmt_xdate()
    fig.tight_layout()
    os.makedirs(os.path.dirname(out_png) or ".", exist_ok=True)
    fig.savefig(out_png, dpi=120)
    plt.close(fig)


def build_report(leaderboard_path: str = "data/leaderboard.csv",
                 out_path: str = "docs/index.html") -> Optional[str]:
    if not os.path.exists(leaderboard_path):
        print(f"[report] Kein leaderboard.csv unter {leaderboard_path}. Nichts zu tun.")
        return None

    lb = pd.read_csv(leaderboard_path)
    if lb.empty:
        print("[report] Leaderboard ist leer.")
        return None

    # Sortieren, ansprechend darstellen
    lb["pnl_pct"] = pd.to_numeric(lb["pnl_pct"], errors="coerce")
    lb["run_date"] = lb["run_date"].astype(str)

    # Plot
    out_dir = os.path.dirname(out_path) or "."
    os.makedirs(out_dir, exist_ok=True)
    png_path = os.path.join(out_dir, "pnl_history.png")
    _plot_pnl_history(lb, png_path)

    # Aggregat pro Modell
    agg = (lb.groupby("model")
             .agg(runs=("run_date", "count"),
                  avg_pnl_pct=("pnl_pct", "mean"),
                  best_pnl_pct=("pnl_pct", "max"),
                  worst_pnl_pct=("pnl_pct", "min"),
                  avg_trades=("trades", "mean"))
             .reset_index()
             .sort_values("avg_pnl_pct", ascending=False))

    # HTML
    style = """
    <style>
      body { font-family: system-ui, sans-serif; max-width: 1100px; margin: 2em auto; padding: 0 1em; }
      h1, h2 { border-bottom: 1px solid #eee; padding-bottom: 0.3em; }
      table { border-collapse: collapse; width: 100%; margin: 1em 0; }
      th, td { border: 1px solid #ddd; padding: 0.4em 0.6em; text-align: right; }
      th { background: #f6f6f6; text-align: left; }
      td:first-child, th:first-child { text-align: left; }
      tr:nth-child(even) { background: #fafafa; }
      .pos { color: #2b8a3e; font-weight: 600; }
      .neg { color: #c92a2a; font-weight: 600; }
      img { max-width: 100%; height: auto; margin: 1em 0; }
      code { background: #f4f4f4; padding: 0.1em 0.3em; border-radius: 3px; }
    </style>
    """

    def _fmt_pct(v):
        try:
            v = float(v)
        except (TypeError, ValueError):
            return "—"
        cls = "pos" if v > 0 else ("neg" if v < 0 else "")
        return f'<span class="{cls}">{v:+.2f} %</span>'

    # Aggregat-Tabelle
    agg_rows = ""
    for _, row in agg.iterrows():
        agg_rows += (
            f"<tr>"
            f"<td>{escape(str(row['model']))}</td>"
            f"<td>{int(row['runs'])}</td>"
            f"<td>{_fmt_pct(row['avg_pnl_pct'])}</td>"
            f"<td>{_fmt_pct(row['best_pnl_pct'])}</td>"
            f"<td>{_fmt_pct(row['worst_pnl_pct'])}</td>"
            f"<td>{row['avg_trades']:.1f}</td>"
            f"</tr>"
        )

    # Letzter Lauf pro Modell
    last_date = lb["run_date"].max()
    last_runs = lb[lb["run_date"] == last_date].sort_values("pnl_pct", ascending=False)
    last_rows = ""
    for _, row in last_runs.iterrows():
        last_rows += (
            f"<tr>"
            f"<td>{escape(str(row['model']))}</td>"
            f"<td>{escape(str(row.get('prompt_version', '')))}</td>"
            f"<td>{row['trades']}</td>"
            f"<td>{row['start_total']:.2f}</td>"
            f"<td>{row['end_total']:.2f}</td>"
            f"<td>{_fmt_pct(row['pnl_pct'])}</td>"
            f"<td>{'✔' if row.get('audit_ok') else '✘'}</td>"
            f"</tr>"
        )

    html = f"""<!DOCTYPE html>
<html lang="de">
<head><meta charset="utf-8"><title>AgentTrader — Benchmark</title>{style}</head>
<body>
  <h1>AgentTrader — täglicher Modell-Benchmark</h1>
  <p>
    Automatisch generiert aus <code>{escape(leaderboard_path)}</code>.
    Insgesamt {len(lb)} Läufe, {lb['model'].nunique()} Modelle,
    Zeitraum {lb['run_date'].min()} bis {lb['run_date'].max()}.
  </p>

  <h2>Letzter Lauf ({escape(str(last_date))})</h2>
  <table>
    <thead><tr>
      <th>Modell</th><th>Prompt</th><th>Trades</th>
      <th>Start</th><th>Ende</th><th>P&L %</th><th>Audit</th>
    </tr></thead>
    <tbody>{last_rows}</tbody>
  </table>

  <h2>Aggregat (alle Läufe)</h2>
  <table>
    <thead><tr>
      <th>Modell</th><th>Runs</th><th>Ø P&L %</th>
      <th>Best %</th><th>Worst %</th><th>Ø Trades</th>
    </tr></thead>
    <tbody>{agg_rows}</tbody>
  </table>

  <h2>Verlauf</h2>
  <img src="pnl_history.png" alt="P&L history per model">
</body>
</html>
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[report] geschrieben nach {out_path}")
    return out_path


def _parse():
    p = argparse.ArgumentParser()
    p.add_argument("--leaderboard", type=str, default="data/leaderboard.csv")
    p.add_argument("--out", type=str, default="docs/index.html")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse()
    build_report(args.leaderboard, args.out)