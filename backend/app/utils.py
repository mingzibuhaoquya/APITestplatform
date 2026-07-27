import json
from datetime import datetime
from typing import Any


TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def parse_json(raw: str | None, default: Any) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default


def dump_json(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False)


def fmt_time(value: datetime | None) -> str | None:
    return value.strftime(TIME_FORMAT) if value else None

