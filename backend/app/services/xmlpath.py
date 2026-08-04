from typing import Any
import xml.etree.ElementTree as ET


def _strip_namespaces(element: ET.Element) -> None:
    if "}" in element.tag:
        element.tag = element.tag.split("}", 1)[1]
    for key in list(element.attrib):
        if "}" in key:
            element.attrib[key.split("}", 1)[1]] = element.attrib.pop(key)
    for child in list(element):
        _strip_namespaces(child)


def _normalize_path(root: ET.Element, path: str) -> tuple[str, str | None]:
    expression = path.strip()
    attribute = None
    if "/@" in expression:
        expression, attribute = expression.rsplit("/@", 1)
    if expression.startswith("/"):
        parts = [part for part in expression.split("/") if part]
        if parts and parts[0] == root.tag:
            parts = parts[1:]
        expression = "./" + "/".join(parts) if parts else "."
    elif not expression.startswith((".", "/")):
        expression = f".//{expression}"
    return expression, attribute


def find_xmlpath(text: str, path: str) -> list[Any]:
    if not text or not path.strip():
        return []
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return []
    _strip_namespaces(root)
    expression, attribute = _normalize_path(root, path)
    try:
        elements = [root] if expression == "." else root.findall(expression)
    except SyntaxError:
        return []
    values: list[Any] = []
    for element in elements:
        if attribute:
            value = element.attrib.get(attribute)
        else:
            value = "".join(element.itertext()).strip()
        if value is not None:
            values.append(value)
    return values
