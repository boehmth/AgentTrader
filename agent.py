# agent.py — CLI-Einstieg für einen einzelnen Agent-Lauf.

import argparse
import os

from dotenv import load_dotenv
load_dotenv()

from runner import run_agent
from model import set_model


DEFAULT_GOAL = (
    "Analysiere die aktuellen Preise und entscheide für heute, "
    "ob du kaufst, verkaufst oder abwartest. "
    "Beachte den vorhandenen Portfolio-Zustand."
)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--goal", type=str, default=DEFAULT_GOAL)
    p.add_argument("--as-of", type=str, default=None,
                   help="Simuliertes 'heutiges' Datum (YYYY-MM-DD).")
    p.add_argument("--model", type=str, default=None,
                   help="SAP GenAI Hub Modell (überschreibt SAP_GENAI_MODEL).")
    p.add_argument("--prompt-version", type=str, default=None,
                   help="prompts/<version>/ (überschreibt PROMPT_VERSION).")
    args = p.parse_args()

    if args.model:
        set_model(args.model)
    if args.prompt_version:
        os.environ["PROMPT_VERSION"] = args.prompt_version

    result = run_agent(args.goal, as_of=args.as_of)
    print("\n--- Ergebnis ---")
    print(result)


if __name__ == "__main__":
    main()