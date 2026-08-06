from sqlalchemy.orm import Session

from ..models import Role
from ..utils import dump_json, parse_json


MENU_TREE = [
    {"key": "dashboard", "label": "数据概览", "module": "dashboard"},
    {
        "key": "project-env",
        "label": "项目环境",
        "children": [
            {"key": "projects", "label": "项目管理", "module": "project"},
            {"key": "environments", "label": "环境管理", "module": "environment"},
        ],
    },
    {"key": "apis", "label": "接口管理", "module": "api"},
    {"key": "cases", "label": "用例管理", "module": "case"},
    {"key": "execute", "label": "测试计划", "module": "execute"},
    {"key": "reports", "label": "报告中心", "module": "report"},
    {"key": "logs", "label": "日志中心", "module": "log"},
    {
        "key": "system",
        "label": "系统管理",
        "children": [
            {"key": "accounts", "label": "用户管理", "module": "user"},
            {"key": "roles", "label": "角色管理", "module": "role"},
        ],
    },
]

DEFAULT_ROLE_MENUS = {
    "admin": ["dashboard", "projects", "environments", "apis", "cases", "execute", "reports", "logs", "accounts", "roles"],
    "tester": ["dashboard", "projects", "environments", "apis", "cases", "execute", "reports", "logs", "accounts"],
}

PATH_MENU_RULES = [
    ("/users", {"accounts"}),
    ("/roles", {"roles", "accounts"}),
    ("/projects", {"projects"}),
    ("/environments", {"environments"}),
    ("/apis", {"apis"}),
    ("/cases", {"cases"}),
    ("/scenarios", {"cases"}),
    ("/plans", {"execute"}),
    ("/logs", {"logs"}),
    ("/executions", {"execute", "reports"}),
]


def flat_menu_keys() -> list[str]:
    keys: list[str] = []
    for item in MENU_TREE:
        if children := item.get("children"):
            keys.extend(child["key"] for child in children)
        else:
            keys.append(item["key"])
    return keys


def normalize_menus(menus) -> list[str]:
    allowed = set(flat_menu_keys())
    normalized = []
    for key in menus or []:
        if key in allowed and key not in normalized:
            normalized.append(key)
    if "dashboard" not in normalized:
        normalized.insert(0, "dashboard")
    return normalized


def role_menus(role: Role | None, role_code: str = "") -> list[str]:
    if role and role.status == "active":
        return normalize_menus(parse_json(role.menus_json, DEFAULT_ROLE_MENUS.get(role.code, ["dashboard"])))
    return normalize_menus(DEFAULT_ROLE_MENUS.get(role_code, ["dashboard"]))


def ensure_default_roles(db: Session) -> None:
    defaults = [
        ("admin", "管理员", "系统内置管理员角色", True, DEFAULT_ROLE_MENUS["admin"]),
        ("tester", "测试用户", "系统内置测试用户角色", True, DEFAULT_ROLE_MENUS["tester"]),
    ]
    for code, name, description, is_builtin, menus in defaults:
        role = db.query(Role).filter(Role.code == code).first()
        if role:
            if not role.menus_json:
                role.menus_json = dump_json(menus)
            role.name = role.name or name
            role.description = role.description or description
            role.is_builtin = True
            continue
        db.add(Role(code=code, name=name, description=description, status="active", is_builtin=is_builtin, menus_json=dump_json(menus)))
    db.commit()


def required_menus_for_path(path: str) -> set[str]:
    for prefix, menus in PATH_MENU_RULES:
        if path.startswith(prefix):
            return menus
    return set()


def has_menu_permission(db: Session, role_code: str, path: str) -> bool:
    if role_code == "admin":
        return True
    required = required_menus_for_path(path)
    if not required:
        return True
    role = db.query(Role).filter(Role.code == role_code).first()
    menus = set(role_menus(role, role_code))
    return bool(required.intersection(menus))
