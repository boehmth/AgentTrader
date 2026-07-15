# tools/calculator.py — exakte Arithmetik.

from typing import Any, Dict

from .base import AgentTool


class CalculatorTool(AgentTool):
    name = "calculator"
    description = "Führt eine exakte arithmetische Operation auf zwei Zahlen aus."
    parameters = {
        "operation": "add | subtract | multiply | divide",
        "operand1": "number as string",
        "operand2": "number as string",
    }
    returns = '{"result": float}'

    def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        op = args.get("operation")
        try:
            a = float(args.get("operand1"))
            b = float(args.get("operand2"))
        except Exception:
            return {"error": "operands must be numeric strings"}

        if op == "add":
            return {"result": a + b}
        if op == "subtract":
            return {"result": a - b}
        if op == "multiply":
            return {"result": a * b}
        if op == "divide":
            if b == 0:
                return {"error": "division by zero"}
            return {"result": a / b}
        return {"error": f"unsupported operation '{op}'"}