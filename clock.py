# clock.py — Ein globaler "Heute"-Wert, den alle Tools respektieren.
#
# In der Realität ist "heute" das echte Datum. In der Simulation setzt der
# Simulator diesen Wert Schritt für Schritt auf jeden Handelstag.

from datetime import date, datetime
from typing import Optional

_TODAY: Optional[date] = None  # None → echtes Systemdatum verwenden


def set_today(d) -> None:
    """Setzt das simulierte Heute. Akzeptiert date, datetime oder 'YYYY-MM-DD'."""
    global _TODAY
    if d is None:
        _TODAY = None
        return
    if isinstance(d, datetime):
        _TODAY = d.date()
    elif isinstance(d, date):
        _TODAY = d
    elif isinstance(d, str):
        _TODAY = datetime.strptime(d, "%Y-%m-%d").date()
    else:
        raise TypeError(f"unsupported type for today: {type(d)}")


def today() -> date:
    return _TODAY if _TODAY is not None else date.today()


def today_str() -> str:
    return today().strftime("%Y-%m-%d")