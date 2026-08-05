from typing import Any
import xml.etree.ElementTree as ET
import re


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


def _parse_xml_root(text: str) -> ET.Element | None:
    try:
        return ET.fromstring(text)
    except ET.ParseError:
        pass

    match = re.search(r"<([A-Za-z_][\w.\-:]*)\b[^>]*>", text)
    if not match:
        return None
    root_tag = match.group(1)
    start_tag = match.group(0)
    if start_tag.rstrip().endswith("/>"):
        try:
            return ET.fromstring(text[: match.end()])
        except ET.ParseError:
            return None
    close_tag = f"</{root_tag}>"
    close_index = text.find(close_tag, match.end())
    if close_index == -1:
        return None
    try:
        return ET.fromstring(text[: close_index + len(close_tag)])
    except ET.ParseError:
        return None
    return None


def find_xmlpath(text: str, path: str) -> list[Any]:
    if not text or not path.strip():
        return []
    root = _parse_xml_root(text)
    if root is None:
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
