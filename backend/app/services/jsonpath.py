from typing import Any


def find_jsonpath(data: Any, path: str) -> list[Any]:
    """Small JSONPath fallback for $.a.b[0] used by tests and simple deployments."""
    if not path.startswith("$"):
        return []
    tokens: list[str | int] = []
    index = 1
    while index < len(path):
        char = path[index]
        if char == ".":
            index += 1
            start = index
            while index < len(path) and path[index] not in ".[":
                index += 1
            tokens.append(path[start:index])
        elif char == "[":
            end = path.find("]", index)
            if end == -1:
                return []
            raw = path[index + 1:end]
            if raw.isdigit():
                tokens.append(int(raw))
            else:
                tokens.append(raw.strip("'\""))
            index = end + 1
        else:
            return []
    current = [data]
    for token in tokens:
        next_values: list[Any] = []
        for item in current:
            if isinstance(token, int) and isinstance(item, list) and token < len(item):
                next_values.append(item[token])
            elif isinstance(token, str) and isinstance(item, dict) and token in item:
                next_values.append(item[token])
        current = next_values
    return current

