import json
import re
from typing import Any


VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def render_variables(value: Any, variables: dict[str, Any]) -> Any:
    if isinstance(value, str):
        def replace(match: re.Match[str]) -> str:
            key = match.group(1)
            return str(variables.get(key, match.group(0)))
        return VAR_PATTERN.sub(replace, value)
    if isinstance(value, list):
        return [render_variables(item, variables) for item in value]
    if isinstance(value, dict):
        return {key: render_variables(item, variables) for key, item in value.items()}
    return value


def response_json_or_text(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text

