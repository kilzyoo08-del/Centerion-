"""Code generation and static validation. Generated code is NEVER executed here."""
from __future__ import annotations
import ast


def validate_code(code: str, language: str) -> dict:
    language = (language or "text").lower()
    if language == "python":
        try:
            ast.parse(code)
            return {"valid": True, "method": "python-ast", "message": "Синтаксис Python корректен. Код не запускался."}
        except SyntaxError as exc:
            return {"valid": False, "method": "python-ast", "message": f"Синтаксическая ошибка: {exc.msg}, строка {exc.lineno}."}
    if language in {"json"}:
        import json
        try:
            json.loads(code)
            return {"valid": True, "method": "json-parser", "message": "JSON корректен."}
        except Exception as exc:
            return {"valid": False, "method": "json-parser", "message": str(exc)}
    return {"valid": None, "method": "not-configured", "message": f"Автоматическая проверка синтаксиса для {language} пока не настроена. Код не запускался."}
