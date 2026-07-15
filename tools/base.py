# tools/base.py — Basisklasse für alle Agent-Tools.

from typing import Any, Dict


class AgentTool:
    name: str = ""
    description: str = ""
    parameters: Dict[str, str] = {}
    returns: str = ""

    def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError