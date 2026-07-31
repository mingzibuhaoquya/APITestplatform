import hashlib
import json
import multiprocessing
from queue import Empty
from typing import Any

import quickjs


class PreScriptError(Exception):
    """Raised when an interface pre-script cannot be executed safely."""


MAX_LOG_ITEMS = 20
MAX_LOG_LENGTH = 1000
SCRIPT_TIMEOUT_SECONDS = 2.0


def _run_in_sandbox(script: str, variables: dict[str, Any], headers: dict[str, Any], output: Any) -> None:
    logs: list[dict[str, str]] = []

    def add_log(level: str, message: str) -> None:
        if len(logs) < MAX_LOG_ITEMS:
            logs.append({"level": str(level), "message": str(message)[:MAX_LOG_LENGTH]})

    def digest(algorithm: str, value: str) -> str:
        if algorithm not in {"md5", "sha256"}:
            raise ValueError("Unsupported digest algorithm")
        return hashlib.new(algorithm, str(value).encode("utf-8")).hexdigest()

    context = quickjs.Context()
    context.set_memory_limit(8 * 1024 * 1024)
    context.set_max_stack_size(256 * 1024)
    context.add_callable("__pre_script_log", add_log)
    context.add_callable("__pre_script_hash", digest)
    bootstrap = """
const __pre_script_variables = %s;
const __pre_script_headers = %s;
const __pre_script_header_key = (name) => Object.keys(__pre_script_headers)
  .find((key) => key.toLowerCase() === String(name).toLowerCase());
const __pre_script_request_headers = {
  get: (name) => {
    const key = __pre_script_header_key(name);
    return key === undefined ? undefined : __pre_script_headers[key];
  },
  set: (name, value) => {
    const existingKey = __pre_script_header_key(name);
    __pre_script_headers[existingKey === undefined ? String(name) : existingKey] = value == null ? "" : String(value);
  }
};
const pm = {
  environment: {
    get: (name) => __pre_script_variables[String(name)],
    set: (name, value) => { __pre_script_variables[String(name)] = value == null ? "" : String(value); },
    unset: (name) => { delete __pre_script_variables[String(name)]; },
    has: (name) => Object.prototype.hasOwnProperty.call(__pre_script_variables, String(name))
  },
  request: { headers: __pre_script_request_headers }
};
const CryptoJS = {
  MD5: (value) => ({ toString: () => __pre_script_hash("md5", String(value)) }),
  SHA256: (value) => ({ toString: () => __pre_script_hash("sha256", String(value)) })
};
const __pre_script_text = (value) => {
  if (typeof value === "string") return value;
  try { return JSON.stringify(value); } catch (_) { return String(value); }
};
const console = {
  log: (...args) => __pre_script_log("log", args.map(__pre_script_text).join(" ")),
  info: (...args) => __pre_script_log("info", args.map(__pre_script_text).join(" ")),
  warn: (...args) => __pre_script_log("warn", args.map(__pre_script_text).join(" "))
};
""" % (json.dumps(variables, ensure_ascii=False), json.dumps(headers, ensure_ascii=False))

    try:
        context.eval(bootstrap)
        context.eval(script)
        result = context.eval("JSON.stringify(__pre_script_variables)")
        updated_variables = json.loads(result)
    except (quickjs.JSException, ValueError, TypeError, json.JSONDecodeError) as exc:
        output.put({"ok": False, "error": str(exc)})
        return

    if not isinstance(updated_variables, dict):
        output.put({"ok": False, "error": "Pre-script must leave environment variables as an object"})
        return

    output.put({"ok": True, "variables": updated_variables, "headers": json.loads(context.eval("JSON.stringify(__pre_script_headers)")), "logs": logs})


def run_pre_script(script: str, variables: dict[str, Any], headers: dict[str, Any] | None = None) -> list[dict[str, str]]:
    """Run a constrained pre-script and update task variables and headers in place."""
    if not script or not script.strip():
        return []

    headers = headers if headers is not None else {}
    context = multiprocessing.get_context()
    output = context.Queue(maxsize=1)
    process = context.Process(target=_run_in_sandbox, args=(script, dict(variables), dict(headers), output), daemon=True)
    process.start()
    process.join(SCRIPT_TIMEOUT_SECONDS)
    if process.is_alive():
        process.terminate()
        process.join()
        output.close()
        raise PreScriptError(f"Pre-script timed out after {SCRIPT_TIMEOUT_SECONDS * 1000:.0f}ms")

    try:
        payload = output.get(timeout=0.5)
    except Empty as exc:
        raise PreScriptError("Pre-script exited without a result") from exc
    finally:
        output.close()

    if not payload["ok"]:
        raise PreScriptError(payload["error"])

    variables.clear()
    variables.update(payload["variables"])
    headers.clear()
    headers.update(payload["headers"])
    return payload["logs"]
