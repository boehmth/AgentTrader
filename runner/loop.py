# runner/loop.py — Iterations-Schleife des Agenten.
#
# 1. System-Prompt bauen (aus prompts/system_prompt.txt + prompts/tool_descriptions.txt)
# 2. LLM fragen -> JSON-Plan mit "steps" und "done"
# 3. Steps ausführen (mit $results[i].key-Auflösung über runner.refs)
# 4. Wiederholen, bis LLM done=true meldet oder MAX_ITERATIONS erreicht ist
#
# Der Agent kennt ein "as_of"-Datum. Alle Tools richten sich über clock.today()
# nach diesem Datum. Perfekt für Simulation.

import os
import json
from typing import Any, Dict, List, Optional

import clock
from model import call_llm
from tools import TOOLS

from .refs import resolve_args


MAX_ITERATIONS = 5

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PROMPTS_ROOT = os.path.join(_HERE, "prompts")


def _prompt_dir() -> str:
    """Aktives Prompt-Verzeichnis (versioniert).

    Wählt prompts/<PROMPT_VERSION>/ (Default: 'v1').
    Fällt zurück auf prompts/ selbst, wenn es dort .txt-Dateien gibt
    (Rückwärtskompatibilität).
    """
    version = (os.getenv("PROMPT_VERSION") or "v1").strip()
    versioned = os.path.join(_PROMPTS_ROOT, version)
    if os.path.isdir(versioned):
        return versioned
    return _PROMPTS_ROOT


# ---------------------------------------------------------
# Prompt zusammenbauen
# ---------------------------------------------------------
def build_system_prompt() -> str:
    pdir = _prompt_dir()
    with open(os.path.join(pdir, "system_prompt.txt"), encoding="utf-8") as f:
        base = f.read()
    with open(os.path.join(pdir, "tool_descriptions.txt"), encoding="utf-8") as f:
        tools_desc = f.read()
    return base.replace("{{tools_description}}", tools_desc)


# ---------------------------------------------------------
# Einen Step ausführen
# ---------------------------------------------------------
def execute_step(step: Dict[str, Any], results: List[Any]) -> Any:
    tool = TOOLS.get(step.get("tool"))
    if not tool:
        return {"error": f"unknown tool '{step.get('tool')}'"}

    args = resolve_args(step.get("args", {}) or {}, results)
    try:
        return tool.run(args)
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------
# Haupt-Loop
# ---------------------------------------------------------
def run_agent(user_goal: str, as_of: Optional[str] = None) -> Dict[str, Any]:
    """Führt den Agenten für einen (simulierten) Tag aus.

    Args:
        user_goal: Ziel-Text an den LLM.
        as_of: Optional "YYYY-MM-DD" — wenn gesetzt, gilt dieses Datum als "heute"
               für alle Tools. Sonst wird das echte Systemdatum verwendet.
    """
    if as_of is not None:
        clock.set_today(as_of)

    day = clock.today_str()
    system_prompt = build_system_prompt()
    results: List[Any] = []

    user_goal_with_date = f"Heutiges Datum: {day}\n\n{user_goal}"

    for it in range(1, MAX_ITERATIONS + 1):
        print(f"\n===== [{day}] Iteration {it}/{MAX_ITERATIONS} =====")

        user_prompt = user_goal_with_date
        if results:
            user_prompt += (
                "\n\nBisherige results:\n"
                + json.dumps(results, ensure_ascii=False, indent=2, default=str)
                + '\n\nFahre fort. Wenn fertig: {"steps": [], "done": true}.'
            )

        plan = call_llm(system_prompt, user_prompt)
        # ensure_ascii=True: verhindert UnicodeEncodeError auf cp1252-Konsolen (Windows).
        print("Plan:", json.dumps(plan, ensure_ascii=True, indent=2, default=str))

        if not isinstance(plan, dict) or "steps" not in plan:
            return {"error": "invalid_plan", "raw": plan, "results": results, "day": day}

        for step in plan.get("steps") or []:
            print(f"  Step {len(results)}: {step.get('tool')} "
                  f"{step.get('args', {}).get('operation', '')}")
            r = execute_step(step, results)
            print(f"    -> {r}")
            results.append(r)

        if plan.get("done") is True:
            break
        if not plan.get("steps"):
            break

    return {"day": day, "results": results}