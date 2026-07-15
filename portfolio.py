# tools/portfolio.py — Cash + Holdings.

import os
from typing import Any, Dict

import pandas as pd

import clock

from .base import AgentTool
from .prices import TICKERS


# Default-Pfade. Können per Env-Variable oder per set_data_dir() zur Laufzeit
# geändert werden (z. B. für Benchmark-Läufe mit mehreren Modellen parallel).
_DATA_DIR = os.getenv("DATA_DIR", "data")


def _paths():
    return (
        os.path.join(_DATA_DIR, "portfolio.csv"),
        os.path.join(_DATA_DIR, "trades.csv"),
    )


def set_data_dir(path: str) -> None:
    """Setze zur Laufzeit das Ausgabe-Verzeichnis für portfolio.csv/trades.csv."""
    global _DATA_DIR, PORTFOLIO_FILE, TRADES_FILE
    _DATA_DIR = path
    PORTFOLIO_FILE, TRADES_FILE = _paths()


PORTFOLIO_FILE, TRADES_FILE = _paths()


class PortfolioTool(AgentTool):
    name = "portfolio"
    description = (
        "Verwaltet Cash und Aktienbestände. Der Anfangszustand muss vorab "
        "in data/portfolio.csv stehen (der Simulator oder ein Setup-Skript "
        "legt das an). "
        "load: aktueller Zustand. "
        "buy: kauft N Aktien zu Preis P (Cash sinkt um N*P, Bestand steigt um N). "
        "sell: verkauft N Aktien zu Preis P (Cash steigt um N*P, Bestand sinkt um N)."
    )
    parameters = {
        "operation": "load | buy | sell",
        "operand1": "ticker for buy/sell; '' for load",
        "operand2": (
            "for buy/sell: '<shares>@<price>' (e.g. '2@145.30'); "
            "for load: ''"
        ),
    }
    returns = (
        '{"date": str, "cash": float, "holdings": {ticker: shares, ...}} '
        'or {"error": str}'
    )

    # ---------- helpers ----------
    @staticmethod
    def _empty_df() -> pd.DataFrame:
        return pd.DataFrame(columns=["date", "cash"] + TICKERS)

    @staticmethod
    def _load_df() -> pd.DataFrame:
        try:
            df = pd.read_csv(PORTFOLIO_FILE)
        except FileNotFoundError:
            return PortfolioTool._empty_df()
        for t in TICKERS:
            if t not in df.columns:
                df[t] = 0.0
        for col in ("date", "cash"):
            if col not in df.columns:
                df[col] = 0.0 if col == "cash" else ""
        return df

    @staticmethod
    def _state(df: pd.DataFrame) -> Dict[str, Any]:
        if df.empty:
            return {
                "date": clock.today_str(),
                "cash": 0.0,
                "holdings": {t: 0.0 for t in TICKERS},
            }
        last = df.iloc[-1]
        return {
            "date": str(last["date"]),
            "cash": float(last["cash"]),
            "holdings": {t: float(last[t]) for t in TICKERS},
        }

    @staticmethod
    def _save(state: Dict[str, Any]) -> None:
        os.makedirs(_DATA_DIR, exist_ok=True)
        df = PortfolioTool._load_df()
        row = {"date": clock.today_str(), "cash": state["cash"]}
        for t in TICKERS:
            row[t] = state["holdings"][t]
        new_row = pd.DataFrame([row])
        df = new_row if df.empty else pd.concat([df, new_row], ignore_index=True)
        df.to_csv(PORTFOLIO_FILE, index=False)
        state["date"] = row["date"]

    @staticmethod
    def _parse_shares_at_price(s: str):
        try:
            left, right = s.split("@", 1)
            return float(left), float(right)
        except Exception:
            return None, None

    @staticmethod
    def _log_trade(action: str, ticker: str, shares: float, price: float,
                   cash_delta: float, cash_after: float) -> None:
        os.makedirs(_DATA_DIR, exist_ok=True)
        row = {
            "date": clock.today_str(),
            "action": action,
            "ticker": ticker or "",
            "shares": float(shares),
            "price": float(price),
            "cash_delta": float(cash_delta),
            "cash_after": float(cash_after),
        }
        header = not os.path.exists(TRADES_FILE)
        pd.DataFrame([row]).to_csv(TRADES_FILE, mode="a", header=header, index=False)

    # ---------- main ----------
    def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        op = args.get("operation")
        ticker = args.get("operand1") or ""
        value = args.get("operand2") or ""

        state = self._state(self._load_df())

        if op == "load":
            return state

        if op in ("buy", "sell"):
            if ticker not in TICKERS:
                return {"error": f"unknown ticker '{ticker}'"}
            shares, price = self._parse_shares_at_price(value)
            if shares is None:
                return {"error": "operand2 must look like '<shares>@<price>' (e.g. '2@145.30')"}
            if shares <= 0 or price <= 0:
                return {"error": "shares and price must be > 0"}

            cost = shares * price
            if op == "buy":
                if cost > state["cash"] + 1e-9:
                    return {
                        "error": f"insufficient cash: need {cost:.2f}, have {state['cash']:.2f}"
                    }
                state["cash"] -= cost
                state["holdings"][ticker] += shares
                cash_delta = -cost
            else:  # sell
                if shares > state["holdings"][ticker] + 1e-9:
                    return {
                        "error": (
                            f"insufficient shares of {ticker}: "
                            f"need {shares}, have {state['holdings'][ticker]}"
                        )
                    }
                state["cash"] += cost
                state["holdings"][ticker] -= shares
                cash_delta = +cost

            self._save(state)
            self._log_trade(op, ticker, shares, price, cash_delta, state["cash"])
            return state

        return {"error": f"unsupported operation '{op}'"}