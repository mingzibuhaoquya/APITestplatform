import json
import re
from typing import Any


ALLOWED_ACTIONS = {"goto", "click", "fill", "select", "wait", "assert_text", "assert_visible", "screenshot"}
ALLOWED_LOCATORS = {"text", "css", "xpath", "placeholder", "role", "ai"}


def generate_ui_steps(db: Any, prompt: str, start_url: str = "", existing_steps: list[dict] | None = None) -> list[dict]:
    text = (prompt or "").strip()
    if not text:
        return []
    steps = _generate_steps_from_model(db, text, start_url, existing_steps or [])
    if steps:
        return steps
    return _generate_steps_locally(text, start_url)


def _generate_steps_from_model(db: Any, prompt: str, start_url: str, existing_steps: list[dict]) -> list[dict]:
    import httpx

    from ..models import AiSetting

    setting = db.query(AiSetting).first()
    if not setting or setting.status != "active" or not setting.provider_url or not setting.model_name:
        return []
    payload = {
        "model": setting.model_name,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是Web UI自动化测试步骤生成助手。只能返回JSON，格式为"
                    "{\"steps\":[{\"action\":\"goto|click|fill|select|wait|assert_text|assert_visible|screenshot\","
                    "\"locator_type\":\"text|css|xpath|placeholder|role|ai\",\"target\":\"\",\"value\":\"\",\"description\":\"\"}]}。"
                    "目标元素不确定时使用 locator_type=ai，并把 target 写成自然语言。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {"prompt": prompt, "start_url": start_url, "existing_steps": existing_steps},
                    ensure_ascii=False,
                ),
            },
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    headers = {"Content-Type": "application/json"}
    if setting.api_key:
        headers["Authorization"] = f"Bearer {setting.api_key}"
    try:
        response = httpx.post(_chat_completions_url(setting.provider_url), json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return _normalize_steps(_extract_steps_json(content))
    except Exception:
        return []


def _chat_completions_url(provider_url: str) -> str:
    value = (provider_url or "").strip().rstrip("/")
    if value.endswith("/chat/completions"):
        return value
    return f"{value}/chat/completions"


def _extract_steps_json(content: str) -> list[dict]:
    text = (content or "").strip()
    if not text:
        return []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}|\[.*\]", text, re.S)
        if not match:
            return []
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("steps"), list):
        return data["steps"]
    return []


def _generate_steps_locally(prompt: str, start_url: str) -> list[dict]:
    steps: list[dict] = []
    if start_url.strip() and not _mentions_goto(prompt):
        steps.append(_step("goto", "css", start_url.strip(), start_url.strip(), "打开目标地址"))
    for sentence in _split_sentences(prompt):
        parsed = _parse_sentence(sentence)
        if parsed:
            steps.append(parsed)
    return _normalize_steps(steps)


def _split_sentences(prompt: str) -> list[str]:
    parts = re.split(r"[\n\r；;。]+", prompt)
    return [part.strip(" \t,，.。") for part in parts if part.strip(" \t,，.。")]


def _parse_sentence(sentence: str) -> dict | None:
    compact = sentence.replace(" ", "")
    if any(word in compact for word in ("截图", "截屏")):
        return _step("screenshot", "css", "", "", sentence)
    if "等待" in compact:
        value = _wait_value(compact)
        return _step("wait", "css", "", value, sentence)
    if _mentions_goto(compact):
        url = _extract_url(sentence) or sentence
        return _step("goto", "css", url, url, sentence)
    if any(word in compact for word in ("断言", "检查", "校验", "看到", "显示")):
        expected = _quoted_text(sentence) or _after_keyword(sentence, ("包含", "存在", "显示", "看到", "文本为")) or sentence
        return _step("assert_text", "text", expected, expected, sentence)
    if any(word in compact for word in ("输入", "填写", "填入")):
        target, value = _target_and_value(sentence, ("输入", "填写", "填入"))
        return _step("fill", "ai", target or sentence, value, sentence)
    if "选择" in compact:
        target, value = _target_and_value(sentence, ("选择",))
        return _step("select", "ai", target or sentence, value, sentence)
    if any(word in compact for word in ("点击", "点一下", "单击")):
        target = _strip_leading_action(sentence, ("点击", "点一下", "单击"))
        return _step("click", "ai", target or sentence, "", sentence)
    return None


def _mentions_goto(text: str) -> bool:
    return any(word in text for word in ("打开", "访问", "进入", "跳转")) or bool(_extract_url(text))


def _extract_url(text: str) -> str:
    match = re.search(r"(https?://[^\s，。；;,]+|/[^\s，。；;,]+)", text)
    return match.group(1) if match else ""


def _quoted_text(text: str) -> str:
    match = re.search(r"[\"'“‘](.+?)[\"'”’]", text)
    return match.group(1).strip() if match else ""


def _after_keyword(text: str, keywords: tuple[str, ...]) -> str:
    for keyword in keywords:
        if keyword in text:
            return text.split(keyword, 1)[1].strip(" ：:，,。")
    return ""


def _target_and_value(text: str, actions: tuple[str, ...]) -> tuple[str, str]:
    value = _quoted_text(text)
    for action in actions:
        if action not in text:
            continue
        rest = text.split(action, 1)[1].strip(" ：:，,。")
        for splitter in ("为", "成", "内容", "值", "：", ":"):
            if splitter in rest:
                left, right = rest.split(splitter, 1)
                return _clean_target(left), value or right.strip(" ：:，,。")
        for splitter in ("到", "至", "在"):
            if splitter in rest:
                left, right = rest.split(splitter, 1)
                return _clean_target(right), value or left.strip(" ：:，,。")
        if not value and " " in rest:
            left, right = rest.rsplit(" ", 1)
            if left.strip() and right.strip():
                return _clean_target(left), right.strip(" ：:，,。")
        for prefix in ("经销商", "融资方", "语言", "项目", "环境", "账号", "用户名", "密码"):
            if rest.startswith(prefix) and len(rest) > len(prefix):
                return prefix, value or rest[len(prefix):].strip(" ：:，,。")
        return _clean_target(rest), value
    return "", value


def _strip_leading_action(text: str, actions: tuple[str, ...]) -> str:
    result = text
    for action in actions:
        result = result.replace(action, "", 1)
    return _clean_target(result)


def _clean_target(text: str) -> str:
    return re.sub(r"(输入框|下拉框|选择框|按钮|元素)$", "", text.strip(" ：:，,。")).strip()


def _wait_value(text: str) -> str:
    match = re.search(r"(\d+)\s*(ms|毫秒|秒|s)?", text, re.I)
    if not match:
        return "1000"
    value = int(match.group(1))
    unit = (match.group(2) or "").lower()
    return str(value * 1000 if unit in {"秒", "s"} else value)


def _step(action: str, locator_type: str, target: str, value: Any, description: str) -> dict:
    return {
        "action": action,
        "locator_type": locator_type,
        "target": str(target or ""),
        "value": str(value or ""),
        "description": description,
    }


def _normalize_steps(steps: list[dict]) -> list[dict]:
    normalized: list[dict] = []
    for item in steps:
        action = str(item.get("action") or "").strip()
        locator_type = str(item.get("locator_type") or "ai").strip()
        if action not in ALLOWED_ACTIONS:
            continue
        if locator_type not in ALLOWED_LOCATORS:
            locator_type = "ai"
        if action in {"goto", "wait", "screenshot"}:
            locator_type = "css"
        normalized.append(
            {
                "action": action,
                "locator_type": locator_type,
                "target": str(item.get("target") or ""),
                "value": str(item.get("value") or ""),
                "description": str(item.get("description") or ""),
            }
        )
    return normalized[:50]
